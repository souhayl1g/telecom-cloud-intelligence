from pathlib import Path
import os

MODELS_DIR = Path(os.getenv("MODELS_DIR", "/app/models"))
MODEL_VERSION = "v2.0"
CACHE_TTL_SECONDS = 30

SLA_MODEL_PATH = MODELS_DIR / "sla_risk_model.joblib"
ANOMALY_MODEL_PATH = MODELS_DIR / "anomaly_model.joblib"
REVENUE_ANOMALY_MODEL_PATH = MODELS_DIR / "revenue_anomaly_model.joblib"

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
