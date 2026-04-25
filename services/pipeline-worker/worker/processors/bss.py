"""BSS data processing — raw → processed layer enrichment + curated join."""
import numpy as np


def build_processed_bss(records: list[dict]) -> list[dict]:
    """Clean + enrich BSS records for the processed data-lake layer."""
    processed = []
    for r in records:
        rec = dict(r)
        rev = r["revenue_tnd"]
        rec["arpu_category"] = "low" if rev < 10 else "mid" if rev < 40 else "high"
        rec["data_intensity"] = round(r["data_used_gb"] / max(rev, 0.01), 4)
        rec["churn_bucket"] = (
            "safe" if r["churn_risk"] < 0.3
            else "watch" if r["churn_risk"] < 0.6
            else "risk"
        )
        processed.append(rec)
    return processed


def build_curated_dataset(
    oss_records, bss_records, anomaly_result,
    rev_anomaly_result, sla_score, correlations,
) -> dict:
    """Build final curated dataset joining OSS + BSS + AI outputs."""
    cell_oss: dict = {}
    for r in oss_records:
        cid = r["cell_id"]
        if cid not in cell_oss:
            cell_oss[cid] = {"tput": [], "lat": [], "loss": [], "rsrp": []}
        cell_oss[cid]["tput"].append(r["throughput_mbps"])
        cell_oss[cid]["lat"].append(r["latency_ms"])
        cell_oss[cid]["loss"].append(r["packet_loss_pct"])
        cell_oss[cid]["rsrp"].append(r["signal_rsrp_dbm"])

    cell_bss: dict = {}
    for r in bss_records:
        cid = r["serving_cell"]
        if cid not in cell_bss:
            cell_bss[cid] = {"rev": [], "data": [], "churn": []}
        cell_bss[cid]["rev"].append(r["revenue_tnd"])
        cell_bss[cid]["data"].append(r["data_used_gb"])
        cell_bss[cid]["churn"].append(r["churn_risk"])

    cells_summary = []
    for cid in sorted(set(list(cell_oss.keys()) + list(cell_bss.keys()))):
        oss = cell_oss.get(cid, {})
        bss = cell_bss.get(cid, {})
        cells_summary.append({
            "cell_id": cid,
            "mean_throughput": round(float(np.mean(oss.get("tput", [0]))), 2),
            "mean_latency": round(float(np.mean(oss.get("lat", [0]))), 2),
            "mean_packet_loss": round(float(np.mean(oss.get("loss", [0]))), 4),
            "mean_revenue_tnd": round(float(np.mean(bss.get("rev", [0]))), 2),
            "mean_data_gb": round(float(np.mean(bss.get("data", [0]))), 2),
            "mean_churn_risk": round(float(np.mean(bss.get("churn", [0]))), 4),
        })

    return {
        "sla_risk_score": sla_score,
        "oss_anomaly_count": anomaly_result.get("anomalous_count", 0),
        "bss_anomaly_count": rev_anomaly_result.get("anomalous_count", 0),
        "correlations": correlations,
        "cells_summary": cells_summary,
        "total_oss_records": len(oss_records),
        "total_bss_records": len(bss_records),
    }
