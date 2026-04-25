from fastapi import APIRouter

from config import (
    MODEL_VERSION,
    SLA_MODEL_PATH,
    ANOMALY_MODEL_PATH,
    REVENUE_ANOMALY_MODEL_PATH,
)
from model_cache import load_models

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@router.post("/models/reload")
def reload_models():
    """Force-reload all ML models from disk. Used by L4 Agent pb-model-retrain playbook."""
    try:
        sla, anomaly, revenue = load_models(force=True)
        return {
            "status": "reloaded",
            "models": {
                "sla_risk": {
                    "loaded": sla is not None,
                    "path": str(SLA_MODEL_PATH),
                },
                "anomaly": {
                    "loaded": anomaly is not None,
                    "path": str(ANOMALY_MODEL_PATH),
                },
                "revenue_anomaly": {
                    "loaded": revenue is not None,
                    "path": str(REVENUE_ANOMALY_MODEL_PATH),
                },
            },
            "model_version": MODEL_VERSION,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
