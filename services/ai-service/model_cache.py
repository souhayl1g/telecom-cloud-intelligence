import time
from pathlib import Path
import joblib

from config import (
    SLA_MODEL_PATH,
    ANOMALY_MODEL_PATH,
    REVENUE_ANOMALY_MODEL_PATH,
)

_cache = {"sla": None, "anomaly": None, "revenue": None, "loaded_at": 0}
_cache_ttl = 30  # reload models every 30 seconds max


def _get_model_file_mtime(path: Path) -> float:
    """Get model file modification time, return 0 if doesn't exist."""
    try:
        return path.stat().st_mtime if path.exists() else 0
    except Exception:
        return 0


def load_models(force: bool = False):
    """Load pre-trained models from disk with caching.

    Models are reloaded if:
    - force=True
    - Cache is empty
    - Model files have been modified since last load

    This allows notebooks to retrain and save models while AI service runs.
    """
    global _cache

    now = time.time()
    should_reload = force or _cache["sla"] is None

    # Check if models need reload based on file mtime
    if not should_reload and now - _cache["loaded_at"] > _cache_ttl:
        sla_mtime = _get_model_file_mtime(SLA_MODEL_PATH)
        anomaly_mtime = _get_model_file_mtime(ANOMALY_MODEL_PATH)
        revenue_mtime = _get_model_file_mtime(REVENUE_ANOMALY_MODEL_PATH)

        if (
            sla_mtime > _cache["loaded_at"]
            or anomaly_mtime > _cache["loaded_at"]
            or revenue_mtime > _cache["loaded_at"]
        ):
            should_reload = True

    if not should_reload:
        return _cache["sla"], _cache["anomaly"], _cache["revenue"]

    missing = []
    for path in [SLA_MODEL_PATH, ANOMALY_MODEL_PATH, REVENUE_ANOMALY_MODEL_PATH]:
        if not path.exists():
            missing.append(str(path))

    if missing and _cache["sla"] is None:
        raise FileNotFoundError(
            f"Pre-trained model(s) not found: {missing}. "
            "Run the training notebooks (notebooks/) to generate model artifacts, "
            "then place them in /app/models/."
        )

    # Reload models if files exist
    try:
        if SLA_MODEL_PATH.exists():
            sla_model = joblib.load(SLA_MODEL_PATH)
            print(f"  [ml] loaded SLA model from {SLA_MODEL_PATH}")
        else:
            sla_model = _cache["sla"]
    except Exception as e:
        print(f"  [ml] warning: failed to reload SLA model: {e}")
        sla_model = _cache["sla"]

    try:
        if ANOMALY_MODEL_PATH.exists():
            anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
            print(f"  [ml] loaded anomaly model from {ANOMALY_MODEL_PATH}")
        else:
            anomaly_model = _cache["anomaly"]
    except Exception as e:
        print(f"  [ml] warning: failed to reload anomaly model: {e}")
        anomaly_model = _cache["anomaly"]

    try:
        if REVENUE_ANOMALY_MODEL_PATH.exists():
            revenue_anomaly_model = joblib.load(REVENUE_ANOMALY_MODEL_PATH)
            print(
                f"  [ml] loaded revenue anomaly model from {REVENUE_ANOMALY_MODEL_PATH}"
            )
        else:
            revenue_anomaly_model = _cache["revenue"]
    except Exception as e:
        print(f"  [ml] warning: failed to reload revenue anomaly model: {e}")
        revenue_anomaly_model = _cache["revenue"]

    _cache["sla"] = sla_model
    _cache["anomaly"] = anomaly_model
    _cache["revenue"] = revenue_anomaly_model
    _cache["loaded_at"] = now

    return sla_model, anomaly_model, revenue_anomaly_model
