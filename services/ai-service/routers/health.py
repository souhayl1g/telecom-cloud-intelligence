from fastapi import APIRouter

from config import (
    MODEL_VERSION,
    CEM_MODEL_PATH,
    RAT_MODEL_PATH,
    VAE_MODEL_PATH,
    VAE_SCALER_PATH,
)
from model_cache import load_models

router = APIRouter()


@router.get("/health")
def health():
    models = load_models()
    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
        "models_loaded": {
            "cem": models.get("cem") is not None,
            "rat_underservice": models.get("rat") is not None,
            "vae_anomaly": models.get("vae") is not None,
        },
    }


@router.post("/models/reload")
def reload_models():
    """Force-reload all v3.0 ML models from disk. Used by L4 Agent pb-model-retrain playbook."""
    try:
        models = load_models(force=True)
        return {
            "status": "reloaded",
            "models": {
                "cem": {
                    "loaded": models.get("cem") is not None,
                    "path": str(CEM_MODEL_PATH),
                },
                "rat_underservice": {
                    "loaded": models.get("rat") is not None,
                    "path": str(RAT_MODEL_PATH),
                },
                "vae_anomaly": {
                    "loaded": models.get("vae") is not None,
                    "path": str(VAE_MODEL_PATH),
                    "scaler_loaded": models.get("vae_scaler") is not None,
                    "scaler_path": str(VAE_SCALER_PATH),
                },
            },
            "model_version": MODEL_VERSION,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
