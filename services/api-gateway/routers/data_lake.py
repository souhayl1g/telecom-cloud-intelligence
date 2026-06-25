"""Converged Data Lake summary.

Surfaces REAL stats for the OSS+BSS "little data lake" so the architecture page
is evidence, not a slide:

  - sources  : Postgres row counts per domain (OSS cell KPIs, BSS subscribers, features)
  - layers   : MinIO object count + bytes per lake layer (raw -> processed -> curated)
  - twin     : Spatio-Temporal Convergence Layer stats (governorates joined = WHERE,
               significant Granger pairs = WHEN)

Honesty contract: any metric that cannot be computed returns null (the UI renders
'—'), never a fabricated 0. Cached for 30s to avoid walking MinIO on every poll.
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor

from db import _db
from auth import require_auth
from services import storage

router = APIRouter()

# 3-layer lake (matches pipeline-worker/worker/config.py BUCKETS).
_LAYERS = ["raw", "processed", "curated"]

_CACHE: dict = {"ts": 0.0, "data": None}
_CACHE_TTL = 120  # seconds — counts change slowly; 2-min cache cuts cold-start penalty


def _scalar(cur, sql: str):
    """Run a query returning a single value, or None on failure."""
    try:
        cur.execute(sql)
        row = cur.fetchone()
        return list(row.values())[0] if row else None
    except Exception:
        return None


def _approx_count(cur, table: str) -> int | None:
    """O(1) row estimate from pg_class statistics (updated by autovacuum).

    Avoids full COUNT(*) scans on 18M-row tables. Returns None when stats
    have not yet been collected (reltuples <= 0), which renders as '—'.
    """
    try:
        cur.execute(
            "SELECT reltuples::bigint FROM pg_class WHERE relname = %s",
            (table,),
        )
        row = cur.fetchone()
        v = list(row.values())[0] if row else None
        return int(v) if v is not None and int(v) > 0 else None
    except Exception:
        return None


def _layer_stats() -> dict:
    """Object count + total bytes per MinIO lake layer. Null per-layer on failure."""
    out = {}
    try:
        s3 = storage.get_s3()
    except Exception:
        return {layer: {"objects": None, "bytes": None} for layer in _LAYERS}
    for layer in _LAYERS:
        objects, total = 0, 0
        try:
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=layer):
                for obj in page.get("Contents", []):
                    objects += 1
                    total += obj.get("Size", 0)
            out[layer] = {"objects": objects, "bytes": total}
        except Exception:
            out[layer] = {"objects": None, "bytes": None}
    return out


@router.get("/data-lake/summary")
def data_lake_summary(user=Depends(require_auth)):
    """Live converged-data-lake snapshot (30s cached)."""
    now = time.time()
    if _CACHE["data"] is not None and (now - _CACHE["ts"]) < _CACHE_TTL:
        return _CACHE["data"]

    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Use pg_class statistics for the two huge tables (18M + 2.4M rows).
                # DISTINCT counts below are small-cardinality and use their indexes.
                sources = {
                    "oss_cell_kpis": _approx_count(cur, "oss_cell_kpis"),
                    "bss_subscribers": _approx_count(cur, "bss_subscribers"),
                    "subscriber_features": _approx_count(cur, "subscriber_features"),
                }
                last_ingest = {
                    "oss": _scalar(cur, "SELECT max(created_at) FROM oss_cell_kpis;"),
                    "bss": _scalar(cur, "SELECT max(created_at) FROM bss_subscribers;"),
                }
                # Spatio-Temporal Convergence Layer (the digital twin):
                #   WHERE = geographic breadth — governorate buckets (BSS side) +
                #           cell-level spatial nodes (OSS side);
                #   joint = the O+B correlation rows the convergence engine persisted.
                # All real counts from real data — no derived/placeholder columns.
                twin = {
                    "governorates_spanned": _scalar(
                        cur, "SELECT count(DISTINCT area) FROM bss_subscribers;"
                    ),
                    "oss_cells_monitored": _scalar(
                        cur, "SELECT count(DISTINCT cell_id) FROM oss_cell_kpis;"
                    ),
                    "convergence_pairs": _scalar(
                        cur, "SELECT count(*) FROM correlation_insights;"
                    ),
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    summary = {
        "sources": sources,
        "last_ingest": last_ingest,
        "layers": _layer_stats(),
        "twin": twin,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _CACHE["data"] = summary
    _CACHE["ts"] = now
    return summary
