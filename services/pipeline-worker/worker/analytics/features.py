"""KPI feature aggregation for ML inference inputs."""

import numpy as np


def compute_oss_features(records: list[dict]) -> dict:
    """Aggregate per-record OSS measurements into features."""
    if not records:
        return {
            "mean_throughput_mbps": 0.0,
            "std_throughput_mbps": 0.0,
            "mean_latency_ms": 0.0,
            "std_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "mean_packet_loss_pct": 0.0,
            "max_packet_loss_pct": 0.0,
            "mean_active_users": 0.0,
            "mean_signal_rsrp_dbm": 0.0,
        }
    tput = np.array(
        [v for v in (r.get("throughput_mbps") for r in records) if v is not None],
        dtype=float,
    )
    lat = np.array(
        [v for v in (r.get("latency_ms") for r in records) if v is not None],
        dtype=float,
    )
    loss = np.array(
        [
            v
            for v in (
                r.get("packet_loss_pct", r.get("packet_loss_rate")) for r in records
            )
            if v is not None
        ],
        dtype=float,
    )
    usr = np.array(
        [v for v in (r.get("active_users") for r in records) if v is not None],
        dtype=float,
    )
    rsrp = np.array(
        [
            v
            for v in (r.get("signal_rsrp_dbm", r.get("rsrp_dbm")) for r in records)
            if v is not None
        ],
        dtype=float,
    )
    return {
        "mean_throughput_mbps": round(float(tput.mean()), 4) if tput.size else None,
        "std_throughput_mbps": round(float(tput.std()), 4) if tput.size else None,
        "mean_latency_ms": round(float(lat.mean()), 4) if lat.size else None,
        "std_latency_ms": round(float(lat.std()), 4) if lat.size else None,
        "max_latency_ms": round(float(lat.max()), 4) if lat.size else None,
        "mean_packet_loss_pct": round(float(loss.mean()), 4) if loss.size else None,
        "max_packet_loss_pct": round(float(loss.max()), 4) if loss.size else None,
        "mean_active_users": round(float(usr.mean()), 4) if usr.size else None,
        "mean_signal_rsrp_dbm": round(float(rsrp.mean()), 4) if rsrp.size else None,
    }


def compute_bss_features(records: list[dict]) -> dict:
    """Aggregate BSS metrics for v3 inference context."""
    if not records:
        return {
            "mean_dou_total": 0.0,
            "mean_duration": 0.0,
            "mean_s1_mme_sr": 0.0,
            "mean_iu_attach_sr": 0.0,
            "mean_gb_attach_sr": 0.0,
            "mean_network_experience_index": 0.0,
        }
    dou = np.array([r["dou_total"] for r in records], dtype=float)
    dur = np.array([r["duration"] for r in records], dtype=float)
    s1 = np.array([r["s1_mme_sr"] for r in records], dtype=float)
    iu = np.array([r["iu_attach_sr"] for r in records], dtype=float)
    gb = np.array([r["gb_attach_sr"] for r in records], dtype=float)
    nei = np.array(
        [r.get("network_experience_index", 0.5) for r in records], dtype=float
    )
    return {
        "mean_dou_total": round(float(dou.mean()), 4),
        "mean_duration": round(float(dur.mean()), 4),
        "mean_s1_mme_sr": round(float(s1.mean()), 4),
        "mean_iu_attach_sr": round(float(iu.mean()), 4),
        "mean_gb_attach_sr": round(float(gb.mean()), 4),
        "mean_network_experience_index": round(float(nei.mean()), 4),
    }
