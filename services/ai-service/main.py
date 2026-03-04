"""
AI Service — Real inference with trained scikit-learn models.

Models trained on startup from synthetic data (if not already persisted):
  sla_risk_model.joblib   — GradientBoostingRegressor
                            Predicts SLA breach risk (0–1) from aggregated KPI features.
  anomaly_model.joblib    — IsolationForest
                            Detects anomalous OSS KPI records from per-record features.

Both models are written to /app/models/ and reloaded on subsequent restarts.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# ── constants ─────────────────────────────────────────────────────────────────

MODELS_DIR    = Path("/app/models")
SLA_MODEL_PATH     = MODELS_DIR / "sla_risk_model.joblib"
ANOMALY_MODEL_PATH = MODELS_DIR / "anomaly_model.joblib"
MODEL_VERSION = "v1.0"
N_TRAIN       = 3000   # synthetic training samples
RANDOM_SEED   = 42

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

# ── training data generators ──────────────────────────────────────────────────

def _generate_sla_training_data(n: int, seed: int):
    """
    Synthesise N windows of aggregated OSS KPI features + risk label.

    Risk label is a deterministic function of the features so the model
    learns a real decision boundary, not noise.
    """
    rng = np.random.default_rng(seed)

    mean_tput  = rng.uniform(10,  120, n)      # Mbps
    std_tput   = rng.uniform( 2,   25, n)
    mean_lat   = rng.uniform( 8,   80, n)      # ms
    std_lat    = rng.uniform( 1,   20, n)
    max_lat    = mean_lat + rng.uniform(5, 40, n)
    mean_loss  = rng.uniform( 0,    5, n)      # pct
    max_loss   = mean_loss + rng.uniform(0, 3, n)
    mean_users = rng.uniform(50,  500, n)
    mean_rsrp  = rng.uniform(-110, -60, n)    # dBm

    X = np.column_stack([
        mean_tput, std_tput, mean_lat, std_lat, max_lat,
        mean_loss, max_loss, mean_users, mean_rsrp,
    ])

    # deterministic risk label: weighted sum of degradation indicators
    risk = np.zeros(n)
    risk += np.clip((mean_lat - 20) / 60,  0, 0.35)   # latency contribution
    risk += np.clip((max_lat  - 30) / 70,  0, 0.25)
    risk += np.clip(mean_loss / 4,          0, 0.25)   # packet loss contribution
    risk += np.clip(max_loss  / 6,          0, 0.15)
    risk += np.clip((60 - mean_tput) / 100, 0, 0.20)  # low throughput contribution
    risk += rng.normal(0, 0.03, n)                     # small noise
    risk  = np.clip(risk, 0.0, 1.0)

    return X, risk


def _generate_anomaly_training_data(n: int, seed: int):
    """
    Synthesise N per-record OSS KPI vectors for IsolationForest training.
    95% normal, 5% injected faults (contamination parameter matches this).
    """
    rng    = np.random.default_rng(seed)
    n_norm = int(n * 0.95)
    n_anom = n - n_norm

    normal = np.column_stack([
        rng.normal(80,  12,  n_norm),     # throughput
        rng.normal(25,   7,  n_norm),     # latency
        rng.uniform(0,   1,  n_norm),     # packet loss
        rng.integers(50, 500, n_norm),    # active users
        rng.normal(-85, 8,   n_norm),     # RSRP
    ])
    anomalous = np.column_stack([
        rng.uniform(1,   20, n_anom),     # very low throughput
        rng.uniform(80, 200, n_anom),     # very high latency
        rng.uniform(3,    8, n_anom),     # high packet loss
        rng.integers(500, 900, n_anom),   # overload or spike
        rng.uniform(-130, -110, n_anom),  # very weak signal
    ])
    X = np.vstack([normal, anomalous])
    idx = rng.permutation(n)
    return X[idx]


# ── model training & persistence ──────────────────────────────────────────────

def _train_sla_model() -> Pipeline:
    print("  [ml] training SLA risk model ...")
    X, y = _generate_sla_training_data(N_TRAIN, RANDOM_SEED)
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("gbr",    GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=RANDOM_SEED,
        )),
    ])
    pipe.fit(X, y)
    importances = pipe.named_steps["gbr"].feature_importances_.tolist()
    print(f"  [ml] SLA model trained — top feature: {SLA_FEATURES[int(np.argmax(importances))]}")
    return pipe


def _train_anomaly_model() -> Pipeline:
    print("  [ml] training anomaly detection model ...")
    X = _generate_anomaly_training_data(N_TRAIN, RANDOM_SEED)
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("ifo",    IsolationForest(
            n_estimators=150,
            contamination=0.05,
            random_state=RANDOM_SEED,
        )),
    ])
    pipe.fit(X)
    print("  [ml] IsolationForest trained")
    return pipe


def load_or_train_models():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if SLA_MODEL_PATH.exists():
        print(f"  [ml] loading SLA model from {SLA_MODEL_PATH}")
        sla_model = joblib.load(SLA_MODEL_PATH)
    else:
        sla_model = _train_sla_model()
        joblib.dump(sla_model, SLA_MODEL_PATH)
        print(f"  [ml] SLA model saved → {SLA_MODEL_PATH}")

    if ANOMALY_MODEL_PATH.exists():
        print(f"  [ml] loading anomaly model from {ANOMALY_MODEL_PATH}")
        anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
    else:
        anomaly_model = _train_anomaly_model()
        joblib.dump(anomaly_model, ANOMALY_MODEL_PATH)
        print(f"  [ml] anomaly model saved → {ANOMALY_MODEL_PATH}")

    return sla_model, anomaly_model


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="AI Service", version=MODEL_VERSION)

# models are loaded at module level so they are ready before the first request
print("[ai-service] initialising models ...")
_sla_model, _anomaly_model = load_or_train_models()
print("[ai-service] models ready")


# ── request / response schemas ────────────────────────────────────────────────

class SlaRiskRequest(BaseModel):
    run_id:       str
    region:       str
    window_start: str
    window_end:   str
    # aggregated KPI features — computed by the pipeline worker
    features: Optional[dict] = None


class OssRecord(BaseModel):
    throughput_mbps:  float
    latency_ms:       float
    packet_loss_pct:  float
    active_users:     int
    signal_rsrp_dbm:  float


class AnomalyRequest(BaseModel):
    run_id:   str
    region:   str
    records:  list[OssRecord]


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.post("/infer/sla-risk")
def infer_sla_risk(req: SlaRiskRequest):
    if req.features:
        # real inference path — pipeline worker sent pre-computed features
        feat_vector = np.array([[
            req.features.get("mean_throughput_mbps", 80.0),
            req.features.get("std_throughput_mbps",  12.0),
            req.features.get("mean_latency_ms",       25.0),
            req.features.get("std_latency_ms",         7.0),
            req.features.get("max_latency_ms",        40.0),
            req.features.get("mean_packet_loss_pct",   0.5),
            req.features.get("max_packet_loss_pct",    1.0),
            req.features.get("mean_active_users",    200.0),
            req.features.get("mean_signal_rsrp_dbm", -85.0),
        ]])
        score = float(np.clip(_sla_model.predict(feat_vector)[0], 0.0, 1.0))
        gbr   = _sla_model.named_steps["gbr"]
        importances = gbr.feature_importances_.tolist()
        explanation = {
            "method":           "GradientBoostingRegressor",
            "feature_importances": dict(zip(SLA_FEATURES, [round(v, 4) for v in importances])),
            "top_driver":       SLA_FEATURES[int(np.argmax(importances))],
            "input_features":   {k: round(v, 4) for k, v in req.features.items()},
            "generated_at":     datetime.now(timezone.utc).isoformat(),
        }
    else:
        # fallback for callers that do not send features
        h     = hashlib.sha256(
            f"{req.run_id}|{req.region}|{req.window_start}|{req.window_end}".encode()
        ).hexdigest()
        score = (int(h[:8], 16) % 100) / 100.0
        explanation = {
            "method":       "deterministic-fallback",
            "note":         "no features provided; result is not model-based",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "score":         score,
        "explanation":   explanation,
        "model_version": MODEL_VERSION,
    }


@app.post("/infer/anomaly")
def infer_anomaly(req: AnomalyRequest):
    if not req.records:
        return {"anomaly_rate": 0.0, "anomalous_count": 0, "total": 0,
                "records": [], "model_version": MODEL_VERSION}

    X = np.array([
        [r.throughput_mbps, r.latency_ms, r.packet_loss_pct,
         float(r.active_users), r.signal_rsrp_dbm]
        for r in req.records
    ])

    # IsolationForest: predict returns +1 (normal) or -1 (anomaly)
    labels      = _anomaly_model.predict(X)           # +1 / -1
    raw_scores  = _anomaly_model.decision_function(X) # negative = more anomalous
    # normalise scores to [0, 1] where 1 = most anomalous
    score_range = raw_scores.max() - raw_scores.min()
    norm_scores = 1.0 - (raw_scores - raw_scores.min()) / (score_range + 1e-9)

    anomaly_mask  = (labels == -1)
    anomaly_count = int(anomaly_mask.sum())
    anomaly_rate  = round(anomaly_count / len(req.records), 4)

    results = [
        {
            "index":         i,
            "is_anomaly":    bool(anomaly_mask[i]),
            "anomaly_score": round(float(norm_scores[i]), 4),
        }
        for i in range(len(req.records))
    ]

    return {
        "run_id":          req.run_id,
        "region":          req.region,
        "total":           len(req.records),
        "anomalous_count": anomaly_count,
        "anomaly_rate":    anomaly_rate,
        "records":         results,
        "model_version":   MODEL_VERSION,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
    }
