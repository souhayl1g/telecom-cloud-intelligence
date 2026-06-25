"""Data drift monitoring (Data Scientist surface).

Computes REAL distribution drift of the model-relevant features across the
monthly snapshots we hold, relative to a baseline month:

  - PSI (Population Stability Index): the standard drift metric.
        PSI = Σ (p_cur - p_base) * ln(p_cur / p_base)   over baseline deciles.
        thresholds: <0.10 stable · 0.10-0.25 moderate · >0.25 significant.
  - KS (binned two-sample Kolmogorov-Smirnov): max |CDF_base - CDF_cur| over the
        same ordered bins. A coarse but honest companion statistic.

No numpy/scipy in this service, so the binning is done in pure Python over a
`TABLESAMPLE` (≈2% block sample) of each month — fast enough to keep the grid
live, cached 5 min. Any cell that cannot be honestly computed (too few rows,
degenerate edges) is returned as null → the UI renders '—', never a fake 0.
"""

import math
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from db import _db
from auth import require_role

router = APIRouter()

# Model-relevant features per source. (column, source_table, human label)
_FEATURES = [
    ("cem_score", "subscriber_features", "CEM Score"),
    ("rat_gap_score", "subscriber_features", "RAT Gap Score"),
    ("network_experience_index", "subscriber_features", "Network Experience"),
    ("data_intensity", "subscriber_features", "Data Intensity"),
]

_N_BINS = 10
_EPS = 1e-6
_CACHE: dict = {}
_CACHE_TTL = 300  # seconds


def _verdict(psi: float | None) -> str | None:
    if psi is None:
        return None
    if psi < 0.10:
        return "stable"
    if psi < 0.25:
        return "moderate"
    return "significant"


def _quantile_edges(sorted_vals: list[float], n_bins: int) -> list[float] | None:
    """Inner bin edges from a sorted sample.

    Zero-inflated / spiky features produce tied quantiles; rather than bail, we
    DEDUPE the edges and bin over the coarser-but-valid grid (PSI is still valid
    with fewer bins). Only a truly constant feature (<2 distinct edges) returns
    None.
    """
    if len(sorted_vals) < n_bins * 2:
        return None
    raw = []
    for i in range(1, n_bins):
        idx = int(i / n_bins * (len(sorted_vals) - 1))
        raw.append(sorted_vals[idx])
    # Strictly-increasing unique edges (collapses ties from zero-inflation).
    edges: list[float] = []
    for e in raw:
        if not edges or e > edges[-1]:
            edges.append(e)
    if len(edges) < 2:  # constant-ish feature — PSI is meaningless
        return None
    return edges


def _bucketize(vals: list[float], edges: list[float]) -> list[float]:
    """Proportion of vals falling in each of the len(edges)+1 bins."""
    counts = [0] * (len(edges) + 1)
    for v in vals:
        lo, hi = 0, len(edges)
        while lo < hi:  # bisect_right
            mid = (lo + hi) // 2
            if v < edges[mid]:
                hi = mid
            else:
                lo = mid + 1
        counts[lo] += 1
    n = len(vals) or 1
    return [c / n for c in counts]


def _psi(p_base: list[float], p_cur: list[float]) -> float:
    total = 0.0
    for b, c in zip(p_base, p_cur):
        b = max(b, _EPS)
        c = max(c, _EPS)
        total += (c - b) * math.log(c / b)
    return total


def _ks_binned(p_base: list[float], p_cur: list[float]) -> float:
    cb = cc = 0.0
    worst = 0.0
    for b, c in zip(p_base, p_cur):
        cb += b
        cc += c
        worst = max(worst, abs(cb - cc))
    return worst


def _feature_drift(cur, column: str, table: str, baseline: str) -> dict:
    """Per-month PSI/KS for one feature vs the baseline month."""
    # One block sample per feature: (month_year, value). ~2% of the table.
    cur.execute(
        f"""
        SELECT month_year, {column} AS v
          FROM {table} TABLESAMPLE SYSTEM (2)
         WHERE {column} IS NOT NULL
        """
    )
    by_month: dict[str, list[float]] = {}
    for row in cur.fetchall():
        by_month.setdefault(row["month_year"], []).append(float(row["v"]))

    base_vals = sorted(by_month.get(baseline, []))
    edges = _quantile_edges(base_vals, _N_BINS)
    p_base = _bucketize(base_vals, edges) if edges else None

    months = []
    for m in sorted(by_month.keys()):
        vals = by_month[m]
        if not edges or p_base is None or len(vals) < _N_BINS * 2:
            months.append(
                {"month": m, "psi": None, "ks": None, "n": len(vals), "verdict": None}
            )
            continue
        p_cur = _bucketize(vals, edges)
        psi = round(_psi(p_base, p_cur), 4)
        ks = round(_ks_binned(p_base, p_cur), 4)
        months.append(
            {"month": m, "psi": psi, "ks": ks, "n": len(vals), "verdict": _verdict(psi)}
        )
    return {"feature": column, "months": months, "n_baseline": len(base_vals)}


@router.get("/drift/summary")
def drift_summary(
    baseline: str = Query("2026-01", description="Reference month (YYYY-MM)"),
    user=Depends(require_role("data_scientist")),
):
    """Drift grid: PSI + KS per feature per month vs the baseline month."""
    key = f"drift::{baseline}"
    now = time.time()
    hit = _CACHE.get(key)
    if hit and (now - hit["ts"]) < _CACHE_TTL:
        return hit["data"]

    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                features = [
                    {**_feature_drift(cur, col, tbl, baseline), "label": label}
                    for col, tbl, label in _FEATURES
                ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    out = {
        "baseline": baseline,
        "features": features,
        "thresholds": {"stable": 0.10, "significant": 0.25},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _CACHE[key] = {"ts": now, "data": out}
    return out
