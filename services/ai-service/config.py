from pathlib import Path
import os

MODELS_DIR = Path(os.getenv("MODELS_DIR", "/app/models"))
MODEL_VERSION = "v3.0"
CACHE_TTL_SECONDS = 30

# v3.0 real-data models (canonical filenames, match notebook training output).
# Legacy *_gpu variants removed 2026-05-24 — single source of truth per model.
CEM_MODEL_PATH = MODELS_DIR / "cem_v3_lightgbm.joblib"
RAT_MODEL_PATH = MODELS_DIR / "rat_underservice_v3_xgb.joblib"
VAE_MODEL_PATH = MODELS_DIR / "oss_vae_v3.pt"
VAE_SCALER_PATH = MODELS_DIR / "vae_v3_scaler.joblib"

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
