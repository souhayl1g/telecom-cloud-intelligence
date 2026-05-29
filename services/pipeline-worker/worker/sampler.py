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
_FALLBACK_MONTH = "2026-04"


def _resolve_default_month() -> str:
    """Return latest month present in bss_subscribers. No caching — daemon
    mode must never sample a stale month.

    Env override SAMPLE_MONTH wins. Falls back to _FALLBACK_MONTH on DB error.
    """
    env = os.getenv("SAMPLE_MONTH")
    if env:
        return env
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(month_year) FROM bss_subscribers")
                row = cur.fetchone()
                return (row and row[0]) or _FALLBACK_MONTH
    except Exception:
        return _FALLBACK_MONTH


# Backwards-compatible module attribute (callers may still reference it).
DEFAULT_MONTH = _FALLBACK_MONTH


def sample_bss_records(n: int = SAMPLE_N, month_year: str | None = None) -> list[dict]:
    """Sample n BSS subscriber records with joined subscriber_features."""
    if month_year is None:
        month_year = _resolve_default_month()
    # Wide SELECT — includes every raw BSS column the v3 CEM and RAT models
    # were trained on, so the inference payload matches the feature contract
    # the routers expect (loaded from cem_v3_feature_names.joblib).
    sql = """
        SELECT b.imsi_hash, b.area, b.generation, b.highest_rat,
               b.volte_flag, b.usim_flag,
               b.dou_total, b.traffic_2g, b.traffic_3g, b.traffic_4g, b.traffic_5g,
               b.duration, b.voice_onlinetime_3g, b.voice_onlinetime_2g,
               b.s1_mme_sr, b.iu_attach_sr, b.gb_attach_sr,
               b.session_flag, b.usertype, b.month_year,
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
        (imsi_hash, area, generation, highest_rat,
         volte_flag, usim_flag,
         dou_total, traffic_2g, traffic_3g, traffic_4g, traffic_5g,
         duration, voice_onlinetime_3g, voice_onlinetime_2g,
         s1, iu, gb, session_flag, usertype, month,
         usim_bottleneck, data_intensity,
         network_experience_index, rat_gap_score) = row
        traffic_total = (traffic_2g or 0) + (traffic_3g or 0) + (traffic_4g or 0) + (traffic_5g or 0)
        result.append({
            "ts": now,
            "subscriber_id": imsi_hash,
            "imsi_hash": imsi_hash,
            "area": area or "Tunis",
            "generation": generation or "4G",
            "highest_rat": highest_rat or "4G",
            "volte_flag": int(volte_flag or 0),
            "usim_flag": int(usim_flag or 0),
            "dou_total": float(dou_total or 0),
            "traffic_2g": float(traffic_2g or 0),
            "traffic_3g": float(traffic_3g or 0),
            "traffic_4g": float(traffic_4g or 0),
            "traffic_5g": float(traffic_5g or 0),
            "duration": float(duration or 0),
            "voice_onlinetime_3g": float(voice_onlinetime_3g or 0),
            "voice_onlinetime_2g": float(voice_onlinetime_2g or 0),
            "s1_mme_sr": float(s1 or 0),
            "iu_attach_sr": float(iu or 0),
            "gb_attach_sr": float(gb or 0),
            "session_flag": int(session_flag or 0),
            "usertype": usertype or "Data User",
            "month_year": month or month_year,
            "usim_bottleneck": 1.0 if usim_bottleneck else 0.0,
            "data_intensity": float(data_intensity or 0),
            "network_experience_index": float(network_experience_index or 0.5),
            "rat_gap_score": float(rat_gap_score or 0),
            # Derived features the v3 models expect alongside the raw cols.
            "traffic_share_2g": (float(traffic_2g or 0) / traffic_total) if traffic_total else 0.0,
            "traffic_share_3g": (float(traffic_3g or 0) / traffic_total) if traffic_total else 0.0,
            "traffic_share_4g": (float(traffic_4g or 0) / traffic_total) if traffic_total else 0.0,
            "traffic_share_5g": (float(traffic_5g or 0) / traffic_total) if traffic_total else 0.0,
            "attach_gap": max(0.0, 1.0 - float(s1 or 0)),
            "is_4g_capable": 1.0 if (generation and ("4G" in generation.upper() or "LTE" in generation.upper() or "5G" in generation.upper())) else 0.0,
            "source": "real",
        })
    return result


def sample_oss_records(n: int = SAMPLE_N, month_year: str | None = None) -> list[dict]:
    """Sample n OSS cell KPI records for the given month."""
    if month_year is None:
        month_year = _resolve_default_month()
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
            "throughput_mbps": float(tput) if tput is not None else None,
            "latency_ms": float(lat) if lat is not None else None,
            "packet_loss_pct": float(loss) if loss is not None else None,
            "jitter_ms": float(jitter) if jitter is not None else None,
            "active_users": int(users) if users is not None else None,
            "signal_rsrp_dbm": float(rsrp) if rsrp is not None else None,
            "cell_load_pct": float(load) if load is not None else None,
            "is_fault": bool(anomaly),
            "source": "real",
        })
    return result
