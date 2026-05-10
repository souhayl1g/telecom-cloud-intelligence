"""OSS↔CEM correlation engine — Pearson + Spearman + Distance Correlation."""
import numpy as np
from scipy import stats

try:
    import dcor
    DCOR_AVAILABLE = True
except ImportError:
    DCOR_AVAILABLE = False
    print("[correlations] dcor not installed — distance correlation skipped")


def compute_correlations(oss_records: list[dict], bss_records: list[dict]) -> list[dict]:
    """Compute Pearson, Spearman, and Distance Correlation between OSS and BSS per area."""
    area_oss: dict = {}
    for r in oss_records:
        area = r.get("area", r.get("cell_id", "unknown"))
        if area not in area_oss:
            area_oss[area] = {"lat": [], "tput": [], "loss": []}
        area_oss[area]["lat"].append(r["latency_ms"])
        area_oss[area]["tput"].append(r["throughput_mbps"])
        area_oss[area]["loss"].append(r.get("packet_loss_pct", r.get("packet_loss_rate", 0)))

    area_bss: dict = {}
    for r in bss_records:
        area = r.get("area", "unknown")
        if area not in area_bss:
            area_bss[area] = {"dou": [], "nei": [], "s1": []}
        area_bss[area]["dou"].append(r["dou_total"])
        area_bss[area]["nei"].append(r.get("network_experience_index", 0.5))
        area_bss[area]["s1"].append(r["s1_mme_sr"])

    common = sorted(set(area_oss.keys()) & set(area_bss.keys()))
    if len(common) < 3:
        return []

    oss_lat = np.array([np.mean(area_oss[c]["lat"]) for c in common])
    oss_tput = np.array([np.mean(area_oss[c]["tput"]) for c in common])
    oss_loss = np.array([np.mean(area_oss[c]["loss"]) for c in common])
    bss_dou = np.array([np.mean(area_bss[c]["dou"]) for c in common])
    bss_nei = np.array([np.mean(area_bss[c]["nei"]) for c in common])
    bss_s1 = np.array([np.mean(area_bss[c]["s1"]) for c in common])

    pairs = [
        ("mean_latency_ms", "mean_network_experience_index", oss_lat, bss_nei),
        ("mean_throughput_mbps", "mean_dou_total", oss_tput, bss_dou),
        ("mean_packet_loss_pct", "mean_s1_mme_sr", oss_loss, bss_s1),
        ("mean_latency_ms", "mean_s1_mme_sr", oss_lat, bss_s1),
        ("mean_throughput_mbps", "mean_network_experience_index", oss_tput, bss_nei),
    ]

    results = []
    for metric_x, metric_y, arr_x, arr_y in pairs:
        for method in ("pearson", "spearman"):
            fn = stats.pearsonr if method == "pearson" else stats.spearmanr
            corr_val, p_val = fn(arr_x, arr_y)
            results.append({
                "metric_x": metric_x,
                "metric_y": metric_y,
                "method": method,
                "corr_value": round(float(corr_val), 6),
                "p_value": round(float(p_val), 6),
            })

        if DCOR_AVAILABLE:
            dc = dcor.distance_correlation(arr_x, arr_y)
            results.append({
                "metric_x": metric_x,
                "metric_y": metric_y,
                "method": "dcor",
                "corr_value": round(float(dc), 6),
                "p_value": None,
            })

    return results
