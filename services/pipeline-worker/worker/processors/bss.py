"""BSS data processing — raw → processed layer enrichment + curated join."""
import numpy as np


def build_processed_bss(records: list[dict]) -> list[dict]:
    """Clean + enrich BSS records for the processed data-lake layer."""
    processed = []
    for r in records:
        rec = dict(r)
        gen = str(r.get("generation", "")).upper()
        rec["generation_4g"] = 1.0 if "4G" in gen or "LTE" in gen else 0.0
        rec["generation_5g"] = 1.0 if "5G" in gen else 0.0
        rat_gap = r.get("rat_gap_score", 0)
        rec["rat_bucket"] = (
            "underserved" if rat_gap > 0.5
            else "matched" if rat_gap < 0.2
            else "watch"
        )
        processed.append(rec)
    return processed


def build_curated_dataset(
    oss_records, bss_records, vae_result,
    cem_result, rat_result, correlations,
) -> dict:
    """Build final curated dataset joining OSS + BSS + v3 AI outputs."""
    area_oss: dict = {}
    for r in oss_records:
        area = r.get("area", r.get("region", "unknown"))
        if area not in area_oss:
            area_oss[area] = {"tput": [], "lat": [], "loss": []}
        area_oss[area]["tput"].append(r["throughput_mbps"])
        area_oss[area]["lat"].append(r["latency_ms"])
        area_oss[area]["loss"].append(r["packet_loss_pct"])

    area_bss: dict = {}
    for r in bss_records:
        area = r.get("area", "unknown")
        if area not in area_bss:
            area_bss[area] = {"dou": [], "nei": [], "duration": []}
        area_bss[area]["dou"].append(r["dou_total"])
        area_bss[area]["nei"].append(r.get("network_experience_index", 0.5))
        area_bss[area]["duration"].append(r["duration"])

    areas_summary = []
    for area in sorted(set(list(area_oss.keys()) + list(area_bss.keys()))):
        oss = area_oss.get(area, {})
        bss = area_bss.get(area, {})
        areas_summary.append({
            "area": area,
            "mean_throughput": round(float(np.mean(oss.get("tput", [0]))), 2),
            "mean_latency": round(float(np.mean(oss.get("lat", [0]))), 2),
            "mean_packet_loss": round(float(np.mean(oss.get("loss", [0]))), 4),
            "mean_dou_total": round(float(np.mean(bss.get("dou", [0]))), 2),
            "mean_network_experience_index": round(float(np.mean(bss.get("nei", [0]))), 4),
        })

    return {
        "vae_anomaly_count": vae_result.get("anomalous_count", 0),
        "vae_anomaly_rate": vae_result.get("anomaly_rate", 0),
        "cem_predictions": len(cem_result.get("predictions", [])),
        "rat_underserved_count": rat_result.get("underserved_count", 0),
        "rat_underserved_rate": rat_result.get("underserved_rate", 0),
        "correlations": correlations,
        "areas_summary": areas_summary,
        "total_oss_records": len(oss_records),
        "total_bss_records": len(bss_records),
    }
