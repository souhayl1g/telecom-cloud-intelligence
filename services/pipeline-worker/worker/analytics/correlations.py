"""OSS↔BSS correlation engine — Pearson + Spearman + Distance Correlation."""
import numpy as np
from scipy import stats

try:
    import dcor
    DCOR_AVAILABLE = True
except ImportError:
    DCOR_AVAILABLE = False
    print("[correlations] dcor not installed — distance correlation skipped")


def compute_correlations(oss_records: list[dict], bss_records: list[dict]) -> list[dict]:
    """Compute Pearson, Spearman, and Distance Correlation between OSS and BSS per cell."""
    cell_oss: dict = {}
    for r in oss_records:
        cid = r["cell_id"]
        if cid not in cell_oss:
            cell_oss[cid] = {"lat": [], "tput": [], "loss": []}
        cell_oss[cid]["lat"].append(r["latency_ms"])
        cell_oss[cid]["tput"].append(r["throughput_mbps"])
        cell_oss[cid]["loss"].append(r["packet_loss_pct"])

    cell_bss: dict = {}
    for r in bss_records:
        cid = r["serving_cell"]
        if cid not in cell_bss:
            cell_bss[cid] = {"rev": [], "data": [], "churn": []}
        cell_bss[cid]["rev"].append(r["revenue_tnd"])
        cell_bss[cid]["data"].append(r["data_used_gb"])
        cell_bss[cid]["churn"].append(r["churn_risk"])

    common = sorted(set(cell_oss.keys()) & set(cell_bss.keys()))
    if len(common) < 3:
        return []

    oss_lat = np.array([np.mean(cell_oss[c]["lat"]) for c in common])
    oss_tput = np.array([np.mean(cell_oss[c]["tput"]) for c in common])
    oss_loss = np.array([np.mean(cell_oss[c]["loss"]) for c in common])
    bss_rev = np.array([np.mean(cell_bss[c]["rev"]) for c in common])
    bss_data = np.array([np.mean(cell_bss[c]["data"]) for c in common])
    bss_churn = np.array([np.mean(cell_bss[c]["churn"]) for c in common])

    pairs = [
        ("mean_latency_ms", "mean_revenue_tnd", oss_lat, bss_rev),
        ("mean_throughput_mbps", "mean_data_used_gb", oss_tput, bss_data),
        ("mean_packet_loss_pct", "mean_churn_risk", oss_loss, bss_churn),
        ("mean_latency_ms", "mean_churn_risk", oss_lat, bss_churn),
        ("mean_throughput_mbps", "mean_revenue_tnd", oss_tput, bss_rev),
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
                "p_value": None,  # dcor is unsigned, no p-value from basic estimator
            })

    return results
