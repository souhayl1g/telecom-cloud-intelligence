"""Operational browsers (Telecom Engineer surface).

Filterable, paginated views the engineer acts on:
  - /oss-cells       : cell KPIs (derived view) with area/RAT/anomaly filters
  - /bss-subscribers : subscriber experience rows with CEM/churn filters

Read-only, capped (LIMIT) and parameterised (no SQL injection). imsi_hash is the
already-hashed identifier; no clear-text subscriber data is exposed.

Performance: both endpoints carry a 15-second in-memory cache keyed on their
query params. The indexes added in migration 008 (idx_sub_feat_cem,
idx_oss_cell_anomaly_ts) allow PG to satisfy ORDER BY ... LIMIT N via an index
scan instead of a full sort on millions of rows.
"""

import hashlib
import json
import time

from fastapi import APIRouter, Depends, Query
from psycopg2.extras import RealDictCursor

from auth import require_role
from db import _db

router = APIRouter()

_BROWSE_CACHE: dict[str, tuple[float, dict]] = {}
_BROWSE_TTL = 15  # seconds


def _cache_get(key: str) -> dict | None:
    entry = _BROWSE_CACHE.get(key)
    if entry and (time.time() - entry[0]) < _BROWSE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: dict) -> None:
    _BROWSE_CACHE[key] = (time.time(), value)


@router.get("/oss-cells")
def oss_cells(
    area: str | None = Query(None),
    rat: str | None = Query(None),
    anomaly: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user=Depends(require_role("engineer")),
):
    """Recent OSS cell KPIs with optional area / RAT / anomaly filters."""
    cache_key = (
        "oss:"
        + hashlib.md5(
            json.dumps(
                {"area": area, "rat": rat, "anomaly": anomaly, "limit": limit}
            ).encode()
        ).hexdigest()
    )
    if cached := _cache_get(cache_key):
        return cached

    where, params = ["1=1"], []
    if area:
        where.append("area = %s")
        params.append(area)
    if rat:
        where.append("rat_type = %s")
        params.append(rat)
    if anomaly is not None:
        where.append("anomaly_flag = %s")
        params.append(anomaly)
    params.append(limit)
    sql = f"""
        SELECT cell_id, area, rat_type, site_name,
               throughput_mbps, latency_ms_derived AS latency_ms,
               packet_loss_pct_derived AS packet_loss_pct,
               cell_load_pct_real AS cell_load_pct,
               integrity, call_drop_rate, rsrp_dbm, active_users,
               anomaly_flag, month_year, timestamp AS ts
          FROM vw_oss_cell_derived
         WHERE {" AND ".join(where)}
         ORDER BY anomaly_flag DESC, timestamp DESC
         LIMIT %s
    """
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    result = {"rows": rows, "count": len(rows)}
    _cache_set(cache_key, result)
    return result


@router.get("/bss-subscribers")
def bss_subscribers(
    month: str | None = Query(None),
    min_cem: float | None = Query(None),
    max_cem: float | None = Query(None),
    churn: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user=Depends(require_role("engineer")),
):
    """Subscriber experience rows (CEM/RAT-gap/churn) + area via a bounded join."""
    cache_key = (
        "bss:"
        + hashlib.md5(
            json.dumps(
                {
                    "month": month,
                    "min_cem": min_cem,
                    "max_cem": max_cem,
                    "churn": churn,
                    "limit": limit,
                }
            ).encode()
        ).hexdigest()
    )
    if cached := _cache_get(cache_key):
        return cached

    where, params = ["1=1"], []
    if month:
        where.append("f.month_year = %s")
        params.append(month)
    if min_cem is not None:
        where.append("f.cem_score >= %s")
        params.append(min_cem)
    if max_cem is not None:
        where.append("f.cem_score <= %s")
        params.append(max_cem)
    if churn is not None:
        where.append("f.churn_risk_flag = %s")
        params.append(churn)
    params.append(limit)
    # Pre-limit on the feature table (uses idx_sub_feat_cem), THEN join.
    sql = f"""
        SELECT f.imsi_hash, f.cem_score, f.rat_gap_score, f.network_experience_index,
               f.churn_risk_flag, f.month_year, b.area, b.usertype, b.highest_rat
          FROM (
              SELECT * FROM subscriber_features f
               WHERE {" AND ".join(where)}
               ORDER BY cem_score ASC
               LIMIT %s
          ) f
          LEFT JOIN bss_subscribers b
                 ON b.imsi_hash = f.imsi_hash AND b.month_year = f.month_year
    """
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    result = {"rows": rows, "count": len(rows)}
    _cache_set(cache_key, result)
    return result
