"""OSS data processing — raw → processed layer enrichment."""


def build_processed_oss(records: list[dict]) -> list[dict]:
    """Clean + enrich OSS records for the processed data-lake layer."""
    processed = []
    for r in records:
        lat = r["latency_ms"]
        tput = r["throughput_mbps"]
        loss = r["packet_loss_pct"]
        usr = r["active_users"]

        lat_severity = (
            "critical" if lat > 80
            else "high" if lat > 50
            else "medium" if lat > 30
            else "normal"
        )
        tput_category = "degraded" if tput < 20 else "fair" if tput < 50 else "good"
        load_factor = round(usr / 500.0, 4) if usr else 0.0
        qos_score = round(max(0.0, 1.0 - (lat / 100) - (loss / 10) + (tput / 200)), 4)

        rec = {k: v for k, v in r.items() if k != "is_fault"}
        rec.update({
            "latency_severity": lat_severity,
            "throughput_category": tput_category,
            "load_factor": load_factor,
            "qos_score": qos_score,
        })
        processed.append(rec)
    return processed
