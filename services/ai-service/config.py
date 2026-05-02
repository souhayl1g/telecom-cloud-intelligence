from pathlib import Path
import os

MODELS_DIR = Path(os.getenv("MODELS_DIR", "/app/models"))
MODEL_VERSION = "v3.0"
CACHE_TTL_SECONDS = 30

# Legacy v2.0 models (kept for backward compatibility)
SLA_MODEL_PATH = MODELS_DIR / "sla_risk_model.joblib"
ANOMALY_MODEL_PATH = MODELS_DIR / "anomaly_model.joblib"
REVENUE_ANOMALY_MODEL_PATH = MODELS_DIR / "revenue_anomaly_model.joblib"

# v3.0 real-data models (GPU-trained on 1.5M+ combined data)
CEM_MODEL_PATH = MODELS_DIR / "cem_v3_lightgbm_gpu.joblib"
CEM_FEATURE_NAMES_PATH = MODELS_DIR / "cem_v3_gpu_features.joblib"
RAT_MODEL_PATH = MODELS_DIR / "rat_v3_xgb_gpu.joblib"
RAT_FEATURE_NAMES_PATH = MODELS_DIR / "rat_v3_gpu_features.joblib"
VAE_MODEL_PATH = MODELS_DIR / "oss_vae_v3_gpu.pt"
VAE_SCALER_PATH = MODELS_DIR / "vae_v3_scaler.joblib"

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

# v3.0 CEM features (from actual area_network_health schema)
CEM_FEATURES = [
    "usim_bottleneck", "data_intensity", "dou_total", "duration",
    "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
    "avg_throughput", "avg_latency", "avg_packet_loss", "anomaly_rate",
    "generation_4g", "generation_5g",
]

# v3.0 RAT features (from actual area_network_health schema)
RAT_FEATURES = [
    "dou_total", "duration", "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
    "network_experience_index", "avg_throughput", "avg_latency", "avg_packet_loss", "anomaly_rate",
]

# v3.0 VAE features (from actual oss_cell_kpis schema — qos_score removed)
VAE_FEATURES = [
    "throughput_mbps", "latency_ms", "packet_loss_rate", "jitter_ms",
    "cell_load_pct", "rsrp_dbm", "active_users", "integrity", "call_drop_rate",
]
