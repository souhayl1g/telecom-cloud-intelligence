"""
AI Service — Real inference with pre-trained scikit-learn models.

Models are loaded dynamically from /app/models/ on each inference request
to support continuous training in notebooks:
  sla_risk_model.joblib            — GradientBoostingRegressor
                                      Predicts SLA breach risk (0–1) from aggregated KPI features.
  anomaly_model.joblib             — IsolationForest
                                      Detects anomalous OSS KPI records from per-record features.
  revenue_anomaly_model.joblib     — IsolationForest
                                      Detects anomalous BSS revenue/usage records.

Training notebooks:
  notebooks/01_data_preparation_eda.ipynb   — Data generation & EDA
  notebooks/02_sla_risk_model.ipynb         — SLA risk model training & evaluation
  notebooks/03_anomaly_detection_models.ipynb — Anomaly models training & evaluation
"""

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

# ── constants ─────────────────────────────────────────────────────────────────

MODELS_DIR = Path("/app/models")
SLA_MODEL_PATH = MODELS_DIR / "sla_risk_model.joblib"
ANOMALY_MODEL_PATH = MODELS_DIR / "anomaly_model.joblib"
REVENUE_ANOMALY_MODEL_PATH = MODELS_DIR / "revenue_anomaly_model.joblib"
MODEL_VERSION = "v2.0"

SLA_FEATURES = [
    "mean_throughput_mbps",
    "std_throughput_mbps",
    "mean_latency_ms",
    "std_latency_ms",
    "max_latency_ms",
    "mean_packet_loss_pct",
    "max_packet_loss_pct",
    "mean_active_users",
    "mean_signal_rsrp_dbm",
]

ANOMALY_FEATURES = [
    "throughput_mbps",
    "latency_ms",
    "packet_loss_pct",
    "active_users",
    "signal_rsrp_dbm",
]

BSS_FEATURES = [
    "revenue_tnd",
    "data_used_gb",
    "voice_min",
    "sms_count",
    "churn_risk",
]

# ── model cache with dynamic reload ─────────────────────────────────────────

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


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="AI Service", version=MODEL_VERSION)

Instrumentator().instrument(app).expose(app)

# Initialize model cache at startup
print("[ai-service] initializing model cache...")
_sla_model, _anomaly_model, _revenue_anomaly_model = load_models(force=True)
print("[ai-service] models ready — 3 models loaded")


# ── request / response schemas ────────────────────────────────────────────────


class SlaRiskRequest(BaseModel):
    run_id: str
    region: str
    window_start: str
    window_end: str
    # aggregated KPI features — computed by the pipeline worker
    features: Optional[dict] = None


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


# ── endpoints ─────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.post("/infer/sla-risk")
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


@app.post("/infer/anomaly")
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


@app.post("/infer/revenue-anomaly")
def infer_revenue_anomaly(req: RevenueAnomalyRequest):
    # Reload models to get latest trained versions
    _, _, _revenue_anomaly_model = load_models()

    """Detect anomalous BSS revenue/usage records with IsolationForest."""
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
