"""
Subscriber Feature Computer + Area Health Aggregator
----------------------------------------------------
Computes derived CEM features from real BSS data + simulated OSS KPIs:

  - rat_gap_score: how underserved is the subscriber? (0=ok, 1=severe)
  - usim_bottleneck: 4G-capable device blocked by 2G SIM
  - data_intensity: data usage per unit of voice activity
  - network_experience_index: weighted combination of attach success rates
  - cem_score_target: composite ground-truth CEM score (0-1)
  - churn_risk_flag: silent user or severe underservice

Also aggregates area-level health metrics into area_network_health table.
"""

import json
import os

import psycopg2
from psycopg2.extras import execute_values, Json

DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel")

# Load cell-to-governorate mapping (OSS cell tower names → BSS governorate names)
_MAPPING_PATH = os.path.join(os.path.dirname(__file__), "cell_governorate_map.json")
CELL_GOVERNORATE_MAP = {}
if os.path.exists(_MAPPING_PATH):
    with open(_MAPPING_PATH) as f:
        CELL_GOVERNORATE_MAP = json.load(f)


def get_conn():
    return psycopg2.connect(DB_URL)


def rat_capability_score(generation: str) -> int:
    """Map device generation to max RAT capability score."""
    g = (generation or "").upper()
    if "5G" in g:
        return 5
    if "LTE" in g or "4G" in g:
        return 4
    if "3G" in g:
        return 3
    if "2G" in g:
        return 2
    return 2  # default conservative


def rat_actual_score(highest_rat: str) -> int:
    r = (highest_rat or "").upper()
    if "5G" in r:
        return 5
    if "4G" in r or "LTE" in r:
        return 4
    if "3G" in r:
        return 3
    if "2G" in r:
        return 2
    return 2  # Unknown treated as 2G for safety


def compute_rat_gap_score(generation: str, highest_rat: str) -> float:
    """0.0 = device capability fully utilized, 1.0 = severely underserved."""
    cap = rat_capability_score(generation)
    act = rat_actual_score(highest_rat)
    gap = cap - act
    return min(1.0, max(0.0, gap / 3.0))  # normalize: gap of 3 = worst


def compute_features_for_month(month_year: str):
    print(f"[features] Computing for {month_year} ...")

    # Fetch all subscribers for this month
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, imsi_hash, generation, highest_rat, usim_flag,
                       dou_total, duration, s1_mme_sr, iu_attach_sr, gb_attach_sr,
                       usertype, area, churned
                FROM bss_subscribers
                WHERE month_year = %s
            """, (month_year,))
            subs = cur.fetchall()

    # Fetch area-level OSS aggregates for this month
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT area,
                       AVG(throughput_mbps) AS avg_tp,
                       AVG(latency_ms) AS avg_lat,
                       AVG(packet_loss_rate) AS avg_pl,
                       AVG(rsrp_dbm) AS avg_rsrp,
                       SUM(CASE WHEN anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count
                FROM oss_cell_kpis
                WHERE month_year = %s
                GROUP BY area
            """, (month_year,))
            raw_oss = {row[0]: row[1:] for row in cur.fetchall()}

    # Remap OSS aggregates from cell tower names → governorates
    oss_agg = {}
    for cell_area, (avg_tp, avg_lat, avg_pl, avg_rsrp, anomaly_count) in raw_oss.items():
        gov = CELL_GOVERNORATE_MAP.get(cell_area)
        if not gov:
            continue
        if gov not in oss_agg:
            oss_agg[gov] = {"tp_sum": 0.0, "lat_sum": 0.0, "pl_sum": 0.0,
                            "rsrp_sum": 0.0, "anomaly_count": 0, "cell_count": 0}
        # Weighted average by cell count (each area aggregate is from one cell area)
        oss_agg[gov]["tp_sum"] += avg_tp or 0
        oss_agg[gov]["lat_sum"] += avg_lat or 0
        oss_agg[gov]["pl_sum"] += avg_pl or 0
        oss_agg[gov]["rsrp_sum"] += avg_rsrp or 0
        oss_agg[gov]["anomaly_count"] += anomaly_count or 0
        oss_agg[gov]["cell_count"] += 1

    # Convert sums to averages
    for gov in oss_agg:
        cnt = oss_agg[gov]["cell_count"]
        oss_agg[gov] = (
            oss_agg[gov]["tp_sum"] / max(cnt, 1),
            oss_agg[gov]["lat_sum"] / max(cnt, 1),
            oss_agg[gov]["pl_sum"] / max(cnt, 1),
            oss_agg[gov]["rsrp_sum"] / max(cnt, 1),
            oss_agg[gov]["anomaly_count"],
        )

    feature_rows = []
    area_stats = {}

    for sub in subs:
        (_id, imsi_hash, generation, highest_rat, usim_flag,
         dou_total, duration, s1_mme_sr, iu_attach_sr, gb_attach_sr,
         usertype, area, churned) = sub
        churned = churned if churned is not None else False

        dou_total = dou_total or 0
        duration = duration or 0
        s1 = s1_mme_sr or 0.0
        iu = iu_attach_sr or 0.0
        gb = gb_attach_sr or 0.0

        rat_gap = compute_rat_gap_score(generation, highest_rat)
        usim_bottleneck = (rat_capability_score(generation) >= 4) and (usim_flag == 0)
        data_intensity = dou_total / (duration + 1.0)

        # Network experience index: weighted average of attach SRs
        # LTE attach is most important, then 3G, then 2G
        ne_index = (s1 * 0.5 + iu * 0.3 + gb * 0.2)

        # CEM score target: composite of usage, quality, device gap
        # Normalize dou_total to ~0-1 (mean ~17GB = 1.7e10 bytes)
        usage_norm = min(1.0, dou_total / 5e10)
        quality_norm = ne_index
        gap_penalty = rat_gap * 0.3  # up to 0.3 penalty
        cem_target = (usage_norm * 0.3 + quality_norm * 0.4) * (1 - gap_penalty)
        cem_target = min(1.0, max(0.0, cem_target))

        # Churn risk: silent user OR severe underservice
        churn_risk = (usertype == "Silent User") or (rat_gap > 0.5 and ne_index < 0.5)

        features_json = {
            "usage_norm": round(usage_norm, 4),
            "quality_norm": round(quality_norm, 4),
            "gap_penalty": round(gap_penalty, 4),
        }

        feature_rows.append((
            imsi_hash, month_year,
            round(rat_gap, 4), usim_bottleneck,
            round(data_intensity, 2), round(ne_index, 4),
            round(cem_target, 4), round(cem_target, 4),  # cem_score = target for now
            churn_risk, churned, Json(features_json)
        ))

        # Accumulate area stats (skip null areas)
        if not area:
            continue
        if area not in area_stats:
            area_stats[area] = {
                "count": 0, "cem_sum": 0.0, "underserved": 0,
                "usim_bottleneck": 0, "anomaly_count": 0,
            }
        area_stats[area]["count"] += 1
        area_stats[area]["cem_sum"] += cem_target
        if rat_gap > 0.5:
            area_stats[area]["underserved"] += 1
        if usim_bottleneck:
            area_stats[area]["usim_bottleneck"] += 1
        area_stats[area]["anomaly_count"] = oss_agg.get(area, (0, 0, 0, 0, 0))[4] or 0

    # Insert subscriber features
    if feature_rows:
        sql = """
            INSERT INTO subscriber_features (
                imsi_hash, month_year, rat_gap_score, usim_bottleneck,
                data_intensity, network_experience_index, cem_score,
                cem_score_target, churn_risk_flag, churned, features_json
            ) VALUES %s
            ON CONFLICT (imsi_hash, month_year) DO UPDATE SET
                rat_gap_score = EXCLUDED.rat_gap_score,
                usim_bottleneck = EXCLUDED.usim_bottleneck,
                data_intensity = EXCLUDED.data_intensity,
                network_experience_index = EXCLUDED.network_experience_index,
                cem_score = EXCLUDED.cem_score,
                cem_score_target = EXCLUDED.cem_score_target,
                churn_risk_flag = EXCLUDED.churn_risk_flag,
                churned = EXCLUDED.churned,
                features_json = EXCLUDED.features_json
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, feature_rows)
            conn.commit()
        print(f"  ... {len(feature_rows)} subscriber features inserted/updated")

    # Insert area health aggregates
    area_rows = []
    for area, stats in area_stats.items():
        oss = oss_agg.get(area, (None, None, None, None, 0))
        area_rows.append((
            area, month_year,
            round(oss[0] or 0, 2), round(oss[1] or 0, 2),
            round(oss[2] or 0, 4), stats["anomaly_count"],
            stats["count"],
            round(stats["cem_sum"] / max(stats["count"], 1), 4),
            round(stats["underserved"] / max(stats["count"], 1) * 100, 2),
            round(stats["usim_bottleneck"] / max(stats["count"], 1) * 100, 2),
            Json({"avg_rsrp": round(oss[3] or 0, 1)}),
        ))

    if area_rows:
        sql = """
            INSERT INTO area_network_health (
                area, month_year, avg_throughput, avg_latency,
                avg_packet_loss, anomaly_count, subscriber_count,
                avg_cem_score, underserved_pct, usim_bottleneck_pct, health_json
            ) VALUES %s
            ON CONFLICT (area, month_year) DO UPDATE SET
                avg_throughput = EXCLUDED.avg_throughput,
                avg_latency = EXCLUDED.avg_latency,
                avg_packet_loss = EXCLUDED.avg_packet_loss,
                anomaly_count = EXCLUDED.anomaly_count,
                subscriber_count = EXCLUDED.subscriber_count,
                avg_cem_score = EXCLUDED.avg_cem_score,
                underserved_pct = EXCLUDED.underserved_pct,
                usim_bottleneck_pct = EXCLUDED.usim_bottleneck_pct,
                health_json = EXCLUDED.health_json
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, area_rows)
            conn.commit()
        print(f"  ... {len(area_rows)} area health rows inserted/updated")


def main():
    months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
    for month in months:
        compute_features_for_month(month)
    print("\n[done] Feature computation complete for all months")


if __name__ == "__main__":
    main()
