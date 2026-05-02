from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

from config import MODEL_VERSION, RAT_FEATURES
from model_cache import load_models

router = APIRouter()


class RatRecord(BaseModel):
    dou_total: float
    duration: float
    s1_mme_sr: float
    iu_attach_sr: float
    gb_attach_sr: float
    network_experience_index: float
    avg_throughput: float
    avg_latency: float
    avg_packet_loss: float
    anomaly_rate: float


class RatRequest(BaseModel):
    run_id: str
    region: str
    records: list[RatRecord]


@router.post("/infer/rat-underservice")
def infer_rat_underservice(req: RatRequest):
    models = load_models()
    rat_model = models.get("rat")

    if rat_model is None:
        return {
            "status": "unavailable",
            "detail": "RAT v3 model not loaded. Run training notebook first.",
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
                for f in RAT_FEATURES
            ]
            for r in req.records
        ],
        dtype=np.float32,
    )

    probs = rat_model.predict_proba(X)[:, 1]
    labels = (probs >= 0.5).astype(int)

    predictions = [
        {
            "index": i,
            "is_underserved": bool(labels[i]),
            "underservice_prob": round(float(probs[i]), 4),
        }
        for i in range(len(req.records))
    ]

    return {
        "run_id": req.run_id,
        "region": req.region,
        "total": len(req.records),
        "underserved_count": int(labels.sum()),
        "underserved_rate": round(float(labels.sum() / len(req.records)), 4),
        "predictions": predictions,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
