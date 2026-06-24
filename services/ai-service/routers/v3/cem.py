from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from config import MODEL_VERSION, CEM_FEATURES
from model_cache import load_models

router = APIRouter()


class CemRecord(BaseModel):
    """Accept any extra fields the trained model expects.

    The router resolves the actual feature contract at inference time from
    `cem_v3_feature_names.joblib` (loaded in model_cache). Missing fields
    default to 0.0 so a partial-feature payload never returns 422 — it
    returns a prediction the model can compute on the columns it has.
    """

    model_config = ConfigDict(extra="allow")


class CemRequest(BaseModel):
    run_id: str
    region: str
    records: list[CemRecord]


@router.post("/infer/cem")
def infer_cem(req: CemRequest):
    models = load_models()
    cem_model = models.get("cem")
    # Prefer the contract trained with the model; fall back to the static list.
    feature_names = models.get("cem_features") or CEM_FEATURES

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

    def _vec(rec: CemRecord) -> list[float]:
        d = rec.model_dump()
        return [float(d.get(f, 0.0) or 0.0) for f in feature_names]

    X = np.array([_vec(r) for r in req.records], dtype=np.float32)

    if X.shape[1] != len(feature_names):
        raise HTTPException(
            status_code=422,
            detail=f"CEM input shape mismatch: expected {len(feature_names)} features, got {X.shape[1]}",
        )

    try:
        preds = cem_model.predict(X)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CEM prediction failed: {e}")

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
