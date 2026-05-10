"""Production Granger causality engine for OSS→CEM temporal impact."""
import json
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests

from worker.db import get_conn

warnings.filterwarnings("ignore")

# Pairs to test: (oss_metric, cem_metric, expected_direction)
CAUSALITY_PAIRS = [
    ("avg_latency", "avg_cem_score", "negative"),
    ("avg_packet_loss", "avg_cem_score", "negative"),
    ("anomaly_count", "underserved_pct", "positive"),
    ("avg_throughput", "avg_cem_score", "positive"),
    ("avg_latency", "underserved_pct", "positive"),
]

MAX_LAG = 2
SIGNIFICANCE_LEVEL = 0.05
MIN_OBSERVATIONS = 4


def _fetch_area_timeseries() -> pd.DataFrame:
    """Fetch area-level monthly aggregates from area_network_health."""
    sql = """
        SELECT area, month_year,
               avg_throughput, avg_latency, avg_packet_loss,
               anomaly_count, subscriber_count, avg_cem_score,
               underserved_pct, usim_bottleneck_pct
        FROM area_network_health
        WHERE area IS NOT NULL
        ORDER BY area, month_year;
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn)
    return df


def _run_granger_test(series_x: pd.Series, series_y: pd.Series, max_lag: int = MAX_LAG) -> dict:
    """Test: does X Granger-cause Y? Return best lag, p-value, F-stat."""
    data = np.column_stack([series_y.values, series_x.values])

    try:
        gc_result = grangercausalitytests(data, maxlag=max_lag, verbose=False)
    except Exception as e:
        return {"error": str(e)}

    best_lag = None
    best_pvalue = 1.0
    best_fstat = 0.0

    for lag, result in gc_result.items():
        pvalue = result[0]["ssr_ftest"][1]
        fstat = result[0]["ssr_ftest"][0]
        if pvalue < best_pvalue:
            best_pvalue = pvalue
            best_fstat = fstat
            best_lag = lag

    return {
        "best_lag": int(best_lag) if best_lag is not None else None,
        "best_pvalue": float(best_pvalue),
        "best_fstat": float(best_fstat),
        "significant": bool(best_pvalue < SIGNIFICANCE_LEVEL),
    }


def _persist_results(results: list[dict]) -> None:
    """Upsert Granger causality results into PostgreSQL."""
    if not results:
        return

    sql = """
        INSERT INTO granger_causality_results
            (area, oss_variable, cem_variable, direction, max_lag,
             best_lag, best_pvalue, best_fstat, significant, test_summary)
        VALUES %s
        ON CONFLICT (area, oss_variable, cem_variable, direction) DO UPDATE SET
            max_lag = EXCLUDED.max_lag,
            best_lag = EXCLUDED.best_lag,
            best_pvalue = EXCLUDED.best_pvalue,
            best_fstat = EXCLUDED.best_fstat,
            significant = EXCLUDED.significant,
            test_summary = EXCLUDED.test_summary,
            created_at = NOW()
    """
    values = [(
        str(r["area"]), str(r["oss_variable"]), str(r["cem_variable"]), str(r["direction"]),
        int(r["max_lag"]),
        int(r["best_lag"]) if r["best_lag"] is not None else None,
        float(r["best_pvalue"]), float(r["best_fstat"]),
        bool(r["significant"]),
        json.dumps(r.get("test_summary", {}))
    ) for r in results]

    with get_conn() as conn:
        from psycopg2.extras import execute_values
        with conn.cursor() as cur:
            execute_values(cur, sql, values)
        conn.commit()


def run_granger_causality() -> dict:
    """Run Granger causality tests and persist results.

    Returns a summary dict with per-pair statistics.
    """
    df = _fetch_area_timeseries()
    if df.empty:
        return {"status": "no_data", "pairs_tested": 0, "significant_findings": 0}

    areas = df["area"].unique()
    all_results = []
    pair_summaries = []

    for oss_metric, cem_metric, expected_dir in CAUSALITY_PAIRS:
        area_results = []
        for area in areas:
            area_df = df[df["area"] == area].sort_values("month_year")
            if len(area_df) < MIN_OBSERVATIONS:
                continue

            x = area_df[oss_metric]
            y = area_df[cem_metric]

            if x.std() == 0 or y.std() == 0:
                continue

            gc = _run_granger_test(x, y, max_lag=MAX_LAG)
            if "error" in gc:
                continue

            area_results.append({
                "area": area,
                "oss_variable": oss_metric,
                "cem_variable": cem_metric,
                "direction": f"{oss_metric}→{cem_metric}",
                "max_lag": MAX_LAG,
                **gc,
            })

        if area_results:
            results_df = pd.DataFrame(area_results)
            n_sig = int(results_df["significant"].sum())
            n_total = len(results_df)
            mean_lag = float(results_df["best_lag"].mean())
            mean_p = float(results_df["best_pvalue"].mean())
            pair_summaries.append({
                "pair": f"{oss_metric}→{cem_metric}",
                "areas_tested": n_total,
                "significant": n_sig,
                "significant_pct": round(n_sig / n_total * 100, 1) if n_total else 0,
                "mean_best_lag": round(mean_lag, 2),
                "mean_pvalue": round(mean_p, 4),
                "expected_direction": expected_dir,
            })
            all_results.extend(area_results)

    _persist_results(all_results)

    summary = {
        "status": "completed",
        "pairs_tested": len(CAUSALITY_PAIRS),
        "areas_with_data": int(len(areas)),
        "significant_findings": sum(p["significant"] for p in pair_summaries),
        "pair_summaries": pair_summaries,
    }

    print(f"[granger] {summary['significant_findings']} significant findings "
          f"across {summary['pairs_tested']} pairs ({summary['areas_with_data']} areas)")
    for ps in pair_summaries:
        print(f"  {ps['pair']}: {ps['significant']}/{ps['areas_tested']} significant "
              f"({ps['significant_pct']}%), mean lag={ps['mean_best_lag']}")

    return summary
