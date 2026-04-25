"""KPI feature aggregation for ML inference inputs."""
import numpy as np


def compute_oss_features(records: list[dict]) -> dict:
    """Aggregate per-record OSS measurements into 9 features for SLA risk model."""
    tput = np.array([r["throughput_mbps"] for r in records], dtype=float)
    lat = np.array([r["latency_ms"] for r in records], dtype=float)
    loss = np.array([r["packet_loss_pct"] for r in records], dtype=float)
    usr = np.array([r["active_users"] for r in records], dtype=float)
    rsrp = np.array([r["signal_rsrp_dbm"] for r in records], dtype=float)
    return {
        "mean_throughput_mbps": round(float(tput.mean()), 4),
        "std_throughput_mbps": round(float(tput.std()), 4),
        "mean_latency_ms": round(float(lat.mean()), 4),
        "std_latency_ms": round(float(lat.std()), 4),
        "max_latency_ms": round(float(lat.max()), 4),
        "mean_packet_loss_pct": round(float(loss.mean()), 4),
        "max_packet_loss_pct": round(float(loss.max()), 4),
        "mean_active_users": round(float(usr.mean()), 4),
        "mean_signal_rsrp_dbm": round(float(rsrp.mean()), 4),
    }


def compute_bss_features(records: list[dict]) -> dict:
    """Aggregate BSS metrics for revenue anomaly context."""
    rev = np.array([r["revenue_tnd"] for r in records], dtype=float)
    data = np.array([r["data_used_gb"] for r in records], dtype=float)
    voice = np.array([r["voice_min"] for r in records], dtype=float)
    sms = np.array([r["sms_count"] for r in records], dtype=float)
    churn = np.array([r["churn_risk"] for r in records], dtype=float)
    return {
        "mean_revenue_tnd": round(float(rev.mean()), 4),
        "std_revenue_tnd": round(float(rev.std()), 4),
        "mean_data_used_gb": round(float(data.mean()), 4),
        "mean_voice_min": round(float(voice.mean()), 4),
        "mean_sms_count": round(float(sms.mean()), 4),
        "mean_churn_risk": round(float(churn.mean()), 4),
    }
