from datetime import datetime, timezone

import numpy as np
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import MODEL_VERSION, VAE_FEATURES
from model_cache import load_models

router = APIRouter()


class VaeRecord(BaseModel):
    throughput_mbps: float
    latency_ms: float
    packet_loss_rate: float
    jitter_ms: float
    cell_load_pct: float
    rsrp_dbm: float
    active_users: int
    integrity: float
    call_drop_rate: float


class VaeRequest(BaseModel):
    run_id: str
    region: str
    records: list[VaeRecord]


@router.post("/infer/vae-anomaly")
def infer_vae_anomaly(req: VaeRequest):
    models = load_models()
    vae_model = models.get("vae")
    scaler = models.get("vae_scaler")
    threshold = models.get("vae_threshold", 0.18)

    if vae_model is None or scaler is None:
        return {
            "status": "unavailable",
            "detail": "VAE v3 model or scaler not loaded. Run training notebook first.",
            "model_version": MODEL_VERSION,
        }

    if not req.records:
        return {
            "run_id": req.run_id,
            "region": req.region,
            "total": 0,
            "records": [],
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    X = np.array(
        [
            [
                getattr(r, f)
                for f in VAE_FEATURES
            ]
            for r in req.records
        ],
        dtype=np.float32,
    )

    if X.shape[1] != len(VAE_FEATURES):
        raise HTTPException(
            status_code=422,
            detail=f"VAE input shape mismatch: expected {len(VAE_FEATURES)} features, got {X.shape[1]}",
        )
    try:
        X_scaled = scaler.transform(X)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        with torch.no_grad():
            recon_errors = vae_model.reconstruction_error(X_tensor).cpu().numpy()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"VAE inference failed: {e}")

    anomaly_mask = recon_errors > threshold
    anomaly_count = int(anomaly_mask.sum())
    anomaly_rate = round(anomaly_count / len(req.records), 4)

    # Normalise anomaly scores to [0, 1] for interpretability
    max_err = recon_errors.max() if recon_errors.max() > 0 else 1.0
    norm_scores = np.clip(recon_errors / max_err, 0.0, 1.0)

    results = [
        {
            "index": i,
            "is_anomaly": bool(anomaly_mask[i]),
            "anomaly_score": round(float(norm_scores[i]), 4),
            "reconstruction_error": round(float(recon_errors[i]), 6),
        }
        for i in range(len(req.records))
    ]

    return {
        "run_id": req.run_id,
        "region": req.region,
        "total": len(req.records),
        "anomalous_count": anomaly_count,
        "anomaly_rate": anomaly_rate,
        "threshold": round(float(threshold), 6),
        "records": results,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
