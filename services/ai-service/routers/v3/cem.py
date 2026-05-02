from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

from config import MODEL_VERSION, CEM_FEATURES
from model_cache import load_models

router = APIRouter()


class CemRecord(BaseModel):
    usim_bottleneck: float
    data_intensity: float
    dou_total: float
    duration: float
    s1_mme_sr: float
    iu_attach_sr: float
    gb_attach_sr: float
    avg_throughput: float
    avg_latency: float
    avg_packet_loss: float
    anomaly_rate: float
    generation_4g: float
    generation_5g: float


class CemRequest(BaseModel):
    run_id: str
    region: str
    records: list[CemRecord]


@router.post("/infer/cem")
def infer_cem(req: CemRequest):
    models = load_models()
    cem_model = models.get("cem")

    if cem_model is None:
        return {
            "status": "unavailable",
            "detail": "CEM v3 model not loaded. Run training notebook first.",
            "model_version": MODEL_VERSION,
        }

    if not req.records:
        return {
            "run_id": req.run_id,
            "region": req.region,
            "total": 0,
            "predictions": [],
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    X = np.array(
        [
            [
                getattr(r, f)
                for f in CEM_FEATURES
            ]
            for r in req.records
        ],
        dtype=np.float32,
    )

    preds = cem_model.predict(X)

    predictions = [
        {
            "index": i,
            "cem_score": round(float(np.clip(p, 0.0, 1.0)), 4),
        }
        for i, p in enumerate(preds)
    ]

    return {
        "run_id": req.run_id,
        "region": req.region,
        "total": len(req.records),
        "predictions": predictions,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
