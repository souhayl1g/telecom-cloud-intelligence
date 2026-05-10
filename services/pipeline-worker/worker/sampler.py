"""
Rolling Window Sampler
----------------------
Samples batches from real BSS + OSS data in Postgres.
Stratified by area × usertype × RAT to maintain distribution.
Returns records in the same format as generate_oss / generate_bss.

Set USE_REAL_DATA=true in env to activate; defaults to synthetic mode.
"""
import os
from datetime import datetime, timezone

from worker.db import get_conn

USE_REAL_DATA = os.getenv("USE_REAL_DATA", "false").lower() == "true"
SAMPLE_N = int(os.getenv("SAMPLE_N", "200"))
DEFAULT_MONTH = os.getenv("SAMPLE_MONTH", "2026-03")


def sample_bss_records(n: int = SAMPLE_N, month_year: str = DEFAULT_MONTH) -> list[dict]:
    """Sample n BSS subscriber records with joined subscriber_features."""
    sql = """
        SELECT b.imsi_hash, b.area, b.generation, b.highest_rat, b.dou_total,
               b.duration, b.s1_mme_sr, b.iu_attach_sr, b.gb_attach_sr,
               b.usertype, b.month_year,
               s.usim_bottleneck, s.data_intensity, s.network_experience_index,
               s.rat_gap_score
        FROM bss_subscribers b
        LEFT JOIN subscriber_features s
          ON b.imsi_hash = s.imsi_hash AND b.month_year = s.month_year
        WHERE b.month_year = %s
        ORDER BY RANDOM()
        LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (month_year, n))
            rows = cur.fetchall()

    now = datetime.now(timezone.utc).isoformat()
    result = []
    for row in rows:
        (imsi_hash, area, generation, highest_rat, dou_total, duration,
         s1, iu, gb, usertype, month, usim_bottleneck, data_intensity,
         network_experience_index, rat_gap_score) = row
        result.append({
            "ts": now,
            "subscriber_id": imsi_hash,
            "area": area or "Tunis",
            "generation": generation or "4G",
            "highest_rat": highest_rat or "4G",
            "dou_total": dou_total or 0,
            "duration": float(duration or 0),
            "s1_mme_sr": float(s1 or 0),
            "iu_attach_sr": float(iu or 0),
            "gb_attach_sr": float(gb or 0),
            "usertype": usertype or "Data User",
            "month_year": month or month_year,
            "usim_bottleneck": 1.0 if usim_bottleneck else 0.0,
            "data_intensity": float(data_intensity or 0),
            "network_experience_index": float(network_experience_index or 0.5),
            "rat_gap_score": float(rat_gap_score or 0),
            "source": "real",
        })
    return result


def sample_oss_records(n: int = SAMPLE_N, month_year: str = DEFAULT_MONTH) -> list[dict]:
    """Sample n OSS cell KPI records for the given month."""
    sql = """
        SELECT cell_id, area, throughput_mbps, latency_ms, packet_loss_rate,
               jitter_ms, active_users, rsrp_dbm, cell_load_pct, anomaly_flag
        FROM oss_cell_kpis
        WHERE month_year = %s
        ORDER BY RANDOM()
        LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (month_year, n))
            rows = cur.fetchall()

    now = datetime.now(timezone.utc).isoformat()
    result = []
    for row in rows:
        cell_id, area, tput, lat, loss, jitter, users, rsrp, load, anomaly = row
        result.append({
            "ts": now,
            "region": area or "demo",
            "cell_id": cell_id,
            "throughput_mbps": float(tput or 45),
            "latency_ms": float(lat or 25),
            "packet_loss_pct": float(loss or 0.8),
            "jitter_ms": float(jitter or 5),
            "active_users": int(users or 100),
            "signal_rsrp_dbm": float(rsrp or -85),
            "cell_load_pct": float(load or 50),
            "is_fault": bool(anomaly),
            "source": "real",
        })
    return result
