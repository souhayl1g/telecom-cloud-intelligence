"""KPI feature aggregation for ML inference inputs."""
import numpy as np


def compute_oss_features(records: list[dict]) -> dict:
    """Aggregate per-record OSS measurements into features."""
    tput = np.array([r["throughput_mbps"] for r in records], dtype=float)
    lat = np.array([r["latency_ms"] for r in records], dtype=float)
    loss = np.array([r.get("packet_loss_pct", r.get("packet_loss_rate", 0)) for r in records], dtype=float)
    usr = np.array([r["active_users"] for r in records], dtype=float)
    rsrp = np.array([r.get("signal_rsrp_dbm", r.get("rsrp_dbm", -85)) for r in records], dtype=float)
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
    """Aggregate BSS metrics for v3 inference context."""
    dou = np.array([r["dou_total"] for r in records], dtype=float)
    dur = np.array([r["duration"] for r in records], dtype=float)
    s1 = np.array([r["s1_mme_sr"] for r in records], dtype=float)
    iu = np.array([r["iu_attach_sr"] for r in records], dtype=float)
    gb = np.array([r["gb_attach_sr"] for r in records], dtype=float)
    nei = np.array([r.get("network_experience_index", 0.5) for r in records], dtype=float)
    return {
        "mean_dou_total": round(float(dou.mean()), 4),
        "mean_duration": round(float(dur.mean()), 4),
        "mean_s1_mme_sr": round(float(s1.mean()), 4),
        "mean_iu_attach_sr": round(float(iu.mean()), 4),
        "mean_gb_attach_sr": round(float(gb.mean()), 4),
        "mean_network_experience_index": round(float(nei.mean()), 4),
    }
