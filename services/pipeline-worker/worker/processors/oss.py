"""OSS data processing — raw → processed layer enrichment."""


def build_processed_oss(records: list[dict]) -> list[dict]:
    """Clean + enrich OSS records for the processed data-lake layer.

    Missing numeric fields (None from DB) propagate as None — no synthetic
    fallbacks, no zeros as dummy replacements.
    """
    processed = []
    for r in records:
        lat = r.get("latency_ms")
        tput = r.get("throughput_mbps")
        loss = r.get("packet_loss_pct")
        usr = r.get("active_users")

        if lat is not None:
            lat_severity = (
                "critical" if lat > 80
                else "high" if lat > 50
                else "medium" if lat > 30
                else "normal"
            )
        else:
            lat_severity = None

        if tput is not None:
            tput_category = "degraded" if tput < 20 else "fair" if tput < 50 else "good"
        else:
            tput_category = None

        if usr is not None:
            load_factor = round(usr / 500.0, 4)
        else:
            load_factor = None

        if lat is not None and loss is not None and tput is not None:
            qos_score = round(max(0.0, 1.0 - (lat / 100) - (loss / 10) + (tput / 200)), 4)
        else:
            qos_score = None

        rec = {k: v for k, v in r.items() if k != "is_fault"}
        rec.update({
            "latency_severity": lat_severity,
            "throughput_category": tput_category,
            "load_factor": load_factor,
            "qos_score": qos_score,
        })
        processed.append(rec)
    return processed
