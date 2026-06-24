"""Data Explorer (Data Scientist surface).

Honest EDA over the curated tables — distributions + basic stats per numeric
feature, computed on a `TABLESAMPLE` block sample (fast on millions of rows).
Aggregates only; no raw confidential rows are exposed. Null/empty where a column
can't be summarised, never fabricated.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from db import _db
from auth import require_role

router = APIRouter()

# Numeric columns worth profiling, per source.
_SOURCES = {
    "bss": {
        "table": "subscriber_features",
        "columns": ["cem_score", "rat_gap_score", "network_experience_index", "data_intensity"],
    },
    "oss": {
        "table": "vw_oss_cell_derived",
        "columns": ["throughput_mbps", "latency_ms_derived", "packet_loss_pct_derived",
                    "cell_load_pct_real", "call_drop_rate"],
    },
}

_BINS = 20
_CACHE: dict = {}
_CACHE_TTL = 300


def _profile(cur, table: str, col: str) -> dict:
    """min/max/avg/median/count + a width_bucket histogram, on a 2% block sample."""
    cur.execute(
        f"""
        WITH s AS (
            SELECT {col}::float8 AS v FROM {table} TABLESAMPLE SYSTEM (2)
             WHERE {col} IS NOT NULL
        ), b AS (
            SELECT min(v) lo, max(v) hi, avg(v) mean,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY v) med, count(*) n
              FROM s
        )
        SELECT lo, hi, mean, med, n FROM b
        """
    )
    stat = cur.fetchone()
    if not stat or stat["n"] is None or stat["n"] == 0 or stat["lo"] is None or stat["hi"] == stat["lo"]:
        return {"column": col, "stats": stat and dict(stat) or None, "histogram": None}

    cur.execute(
        f"""
        WITH s AS (
            SELECT {col}::float8 AS v FROM {table} TABLESAMPLE SYSTEM (2)
             WHERE {col} IS NOT NULL
        )
        SELECT width_bucket(v, %s, %s, %s) AS bucket, count(*) AS c
          FROM s GROUP BY 1 ORDER BY 1
        """,
        (stat["lo"], stat["hi"], _BINS),
    )
    rows = {int(r["bucket"]): int(r["c"]) for r in cur.fetchall()}
    hist = [rows.get(i, 0) for i in range(1, _BINS + 1)]
    return {
        "column": col,
        "stats": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in stat.items()},
        "histogram": hist,
        "bin_lo": round(stat["lo"], 4),
        "bin_hi": round(stat["hi"], 4),
    }


@router.get("/explorer/summary")
def explorer_summary(
    source: str = Query("bss"),
    user=Depends(require_role("data_scientist")),
):
    """Per-feature distribution + stats for one source (bss|oss)."""
    if source not in _SOURCES:
        raise HTTPException(status_code=400, detail="source must be 'bss' or 'oss'")
    key = f"explorer::{source}"
    now = time.time()
    hit = _CACHE.get(key)
    if hit and (now - hit["ts"]) < _CACHE_TTL:
        return hit["data"]

    cfg = _SOURCES[source]
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                features = [_profile(cur, cfg["table"], c) for c in cfg["columns"]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    out = {"source": source, "table": cfg["table"], "bins": _BINS,
           "features": features, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    _CACHE[key] = {"ts": now, "data": out}
    return out
