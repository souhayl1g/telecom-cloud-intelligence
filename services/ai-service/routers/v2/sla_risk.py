import hashlib
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

from config import MODEL_VERSION, SLA_FEATURES
from model_cache import load_models

router = APIRouter()


class SlaRiskRequest(BaseModel):
    run_id: str
    region: str
    window_start: str
    window_end: str
    # aggregated KPI features — computed by the pipeline worker
    features: Optional[dict] = None


@router.post("/infer/sla-risk")
def infer_sla_risk(req: SlaRiskRequest):
    # Reload models to get latest trained versions
    _sla_model, _, _ = load_models()

    if req.features:
        # real inference path — pipeline worker sent pre-computed features
        feat_vector = np.array(
            [
                [
                    req.features.get("mean_throughput_mbps", 80.0),
                    req.features.get("std_throughput_mbps", 12.0),
                    req.features.get("mean_latency_ms", 25.0),
                    req.features.get("std_latency_ms", 7.0),
                    req.features.get("max_latency_ms", 40.0),
                    req.features.get("mean_packet_loss_pct", 0.5),
                    req.features.get("max_packet_loss_pct", 1.0),
                    req.features.get("mean_active_users", 200.0),
                    req.features.get("mean_signal_rsrp_dbm", -85.0),
                ]
            ]
        )
        score = float(np.clip(_sla_model.predict(feat_vector)[0], 0.0, 1.0))
        model = _sla_model.named_steps["model"]
        importances = model.feature_importances_.tolist()
        explanation = {
            "method": "GradientBoostingRegressor",
            "feature_importances": dict(
                zip(SLA_FEATURES, [round(v, 4) for v in importances])
            ),
            "top_driver": SLA_FEATURES[int(np.argmax(importances))],
            "input_features": {k: round(v, 4) for k, v in req.features.items()},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        # fallback for callers that do not send features
        h = hashlib.sha256(
            f"{req.run_id}|{req.region}|{req.window_start}|{req.window_end}".encode()
        ).hexdigest()
        score = (int(h[:8], 16) % 100) / 100.0
        explanation = {
            "method": "deterministic-fallback",
            "note": "no features provided; result is not model-based",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "score": score,
        "explanation": explanation,
        "model_version": MODEL_VERSION,
    }
