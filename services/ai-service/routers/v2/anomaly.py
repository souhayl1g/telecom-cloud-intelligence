from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

from config import MODEL_VERSION
from model_cache import load_models

router = APIRouter()


class OssRecord(BaseModel):
    throughput_mbps: float
    latency_ms: float
    packet_loss_pct: float
    active_users: int
    signal_rsrp_dbm: float


class AnomalyRequest(BaseModel):
    run_id: str
    region: str
    records: list[OssRecord]


@router.post("/infer/anomaly")
def infer_anomaly(req: AnomalyRequest):
    # Reload models to get latest trained versions
    _, _anomaly_model, _ = load_models()

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
            [
                r.throughput_mbps,
                r.latency_ms,
                r.packet_loss_pct,
                float(r.active_users),
                r.signal_rsrp_dbm,
            ]
            for r in req.records
        ]
    )

    # IsolationForest: predict returns +1 (normal) or -1 (anomaly)
    labels = _anomaly_model.predict(X)  # +1 / -1
    raw_scores = _anomaly_model.decision_function(X)  # negative = more anomalous
    # normalise scores to [0, 1] where 1 = most anomalous
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
