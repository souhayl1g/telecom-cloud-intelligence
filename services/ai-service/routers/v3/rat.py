from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from config import MODEL_VERSION, RAT_FEATURES
from model_cache import load_models

router = APIRouter()


class RatRecord(BaseModel):
    """Accepts any extra fields; the router resolves the model's feature
    contract from rat_v3_feature_names.joblib at inference time."""
    model_config = ConfigDict(extra="allow")


class RatRequest(BaseModel):
    run_id: str
    region: str
    records: list[RatRecord]


@router.post("/infer/rat-underservice")
def infer_rat_underservice(req: RatRequest):
    models = load_models()
    rat_model = models.get("rat")
    feature_names = models.get("rat_features") or RAT_FEATURES

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

    def _vec(rec: RatRecord) -> list[float]:
        d = rec.model_dump()
        return [float(d.get(f, 0.0) or 0.0) for f in feature_names]

    X = np.array([_vec(r) for r in req.records], dtype=np.float32)

    if X.shape[1] != len(feature_names):
        raise HTTPException(
            status_code=422,
            detail=f"RAT input shape mismatch: expected {len(feature_names)} features, got {X.shape[1]}",
        )

    try:
        probs = rat_model.predict_proba(X)[:, 1]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"RAT prediction failed: {e}")
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
