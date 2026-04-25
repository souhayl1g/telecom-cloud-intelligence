from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

from config import MODEL_VERSION
from model_cache import load_models

router = APIRouter()


class BssRecord(BaseModel):
    revenue_tnd: float
    data_used_gb: float
    voice_min: float
    sms_count: float
    churn_risk: float


class RevenueAnomalyRequest(BaseModel):
    run_id: str
    region: str
    records: list[BssRecord]


@router.post("/infer/revenue-anomaly")
def infer_revenue_anomaly(req: RevenueAnomalyRequest):
    """Detect anomalous BSS revenue/usage records with IsolationForest."""
    # Reload models to get latest trained versions
    _, _, _revenue_anomaly_model = load_models()
    if not req.records:
        return {
            "anomaly_rate": 0.0,
            "anomalous_count": 0,
            "total": 0,
            "records": [],
            "model_version": MODEL_VERSION,
        }

    X = np.array(
        [
            [r.revenue_tnd, r.data_used_gb, r.voice_min, r.sms_count, r.churn_risk]
            for r in req.records
        ]
    )

    labels = _revenue_anomaly_model.predict(X)
    raw_scores = _revenue_anomaly_model.decision_function(X)
    score_range = raw_scores.max() - raw_scores.min()
    norm_scores = 1.0 - (raw_scores - raw_scores.min()) / (score_range + 1e-9)

    anomaly_mask = labels == -1
    anomaly_count = int(anomaly_mask.sum())
    anomaly_rate = round(anomaly_count / len(req.records), 4)

    results = [
        {
            "index": i,
            "is_anomaly": bool(anomaly_mask[i]),
            "anomaly_score": round(float(norm_scores[i]), 4),
        }
        for i in range(len(req.records))
    ]

    return {
        "run_id": req.run_id,
        "region": req.region,
        "total": len(req.records),
        "anomalous_count": anomaly_count,
        "anomaly_rate": anomaly_rate,
        "records": results,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
