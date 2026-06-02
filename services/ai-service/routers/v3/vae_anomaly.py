import os
from datetime import datetime, timezone

import numpy as np
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from config import MODEL_VERSION, VAE_FEATURES
from model_cache import load_models

# Prefer the feature contract from the trained checkpoint; fall back to static list.
# The router resolves this at inference time so retraining with a different feature
# set does not require a code change.

# When the trained threshold is more than this many orders of magnitude smaller
# than the median reconstruction error of the batch, the checkpoint threshold
# was calibrated on a different data scale than what production traffic sends
# (e.g. raw vs scaled inputs).  We fall back to a batch-derived percentile to
# keep anomaly rates in a sane range. Override via VAE_THRESHOLD_MODE env.
THRESHOLD_MODE = os.environ.get("VAE_THRESHOLD_MODE", "auto")  # auto | static
BATCH_PERCENTILE = float(os.environ.get("VAE_BATCH_PERCENTILE", "95"))

router = APIRouter()


class VaeRecord(BaseModel):
    """Accept any extra fields; the router resolves the model's feature
    contract from the checkpoint at inference time."""
    model_config = ConfigDict(extra="allow")


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
    feature_names = models.get("vae_features") or VAE_FEATURES

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

    def _vec(rec: VaeRecord) -> list[float]:
        d = rec.model_dump()
        return [float(d.get(f, 0.0) or 0.0) for f in feature_names]

    X = np.array([_vec(r) for r in req.records], dtype=np.float32)

    if X.shape[1] != len(feature_names):
        raise HTTPException(
            status_code=422,
            detail=f"VAE input shape mismatch: expected {len(feature_names)} features, got {X.shape[1]}",
        )
    try:
        X_scaled = scaler.transform(X)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        with torch.no_grad():
            recon_errors = vae_model.reconstruction_error(X_tensor).cpu().numpy()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"VAE inference failed: {e}")

    # Autocalibrate threshold when the checkpoint value is wildly mis-scaled.
    effective_threshold = float(threshold)
    threshold_source = "checkpoint"
    if THRESHOLD_MODE == "auto" and len(recon_errors) >= 20:
        median_err = float(np.median(recon_errors))
        if median_err > effective_threshold * 50:  # >50x => scale mismatch
            effective_threshold = float(np.percentile(recon_errors, BATCH_PERCENTILE))
            threshold_source = f"batch_p{int(BATCH_PERCENTILE)}"

    anomaly_mask = recon_errors > effective_threshold
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
        "threshold": round(float(effective_threshold), 6),
        "threshold_source": threshold_source,
        "checkpoint_threshold": round(float(threshold), 6),
        "records": results,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
