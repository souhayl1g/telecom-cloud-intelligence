#!/usr/bin/env python3
"""
Granger Causality Engine — OSS→BSS Temporal Impact Analysis

Computes whether OSS network degradation Granger-causes BSS subscriber
experience degradation at the area level, with optimal lag detection.

Data: 5 months (Jan-May 2026) of area-level aggregates from
      area_network_health table.

Methodology:
  1. Extract time series per area for OSS metrics and BSS metrics
  2. For each area, test: does OSS(t-lag) improve prediction of BSS(t)?
  3. Aggregate across areas for population-level conclusion
  4. Report optimal lag and statistical significance
"""
import os
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2
from scipy import stats
from statsmodels.tsa.stattools import grangercausalitytests

warnings.filterwarnings("ignore")

DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel")

# Pairs to test: (oss_metric, bss_metric, expected_direction)
CAUSALITY_PAIRS = [
    ("avg_latency", "avg_cem_score", "negative"),      # Higher latency → Lower CEM
    ("avg_packet_loss", "avg_cem_score", "negative"),   # Higher loss → Lower CEM
    ("anomaly_count", "underserved_pct", "positive"),   # More anomalies → More underserved
    ("avg_throughput", "avg_cem_score", "positive"),    # Higher throughput → Higher CEM
    ("avg_latency", "underserved_pct", "positive"),     # Higher latency → More underserved
]

MAX_LAG = 2  # months (we only have 5 months, so max lag=2)
SIGNIFICANCE_LEVEL = 0.05


def get_conn():
    return psycopg2.connect(DB_URL)


def fetch_area_timeseries():
    """Fetch area-level monthly aggregates."""
    sql = """
    SELECT area, month_year,
           avg_throughput, avg_latency, avg_packet_loss,
           anomaly_count, subscriber_count, avg_cem_score,
           underserved_pct, usim_bottleneck_pct
    FROM area_network_health
    WHERE month_year IN ('2026-01','2026-02','2026-03','2026-04','2026-05')
    ORDER BY area, month_year;
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn)
    df["month_idx"] = df["month_year"].map({
        "2026-01": 0, "2026-02": 1, "2026-03": 2,
        "2026-04": 3, "2026-05": 4,
    })
    # Normalize anomaly_count to rate
    df["anomaly_rate"] = df["anomaly_count"] / df["subscriber_count"].clip(lower=1)
    return df


def run_granger_test(series_x, series_y, max_lag=2):
    """
    Test: does X Granger-cause Y?
    Returns dict with best lag, p-value, F-statistic, and direction.
    """
    # Stack as [Y, X] for statsmodels
    data = np.column_stack([series_y.values, series_x.values])

    try:
        gc_result = grangercausalitytests(data, maxlag=max_lag, verbose=False)
    except Exception as e:
        return {"error": str(e)}

    best_lag = None
    best_pvalue = 1.0
    best_fstat = 0.0

    for lag, result in gc_result.items():
        # Use ssr_ftest (F-test)
        pvalue = result[0]["ssr_ftest"][1]
        fstat = result[0]["ssr_ftest"][0]
        if pvalue < best_pvalue:
            best_pvalue = pvalue
            best_fstat = fstat
            best_lag = lag

    return {
        "best_lag": best_lag,
        "pvalue": best_pvalue,
        "fstat": best_fstat,
        "significant": best_pvalue < SIGNIFICANCE_LEVEL,
    }


def compute_cross_correlation(series_x, series_y, max_lag=2):
    """Compute normalized cross-correlation at different lags."""
    x = (series_x - series_x.mean()) / series_x.std()
    y = (series_y - series_y.mean()) / series_y.std()
    n = len(x)
    correlations = {}
    for lag in range(0, max_lag + 1):
        if lag == 0:
            corr = np.corrcoef(x, y)[0, 1]
        else:
            corr = np.corrcoef(x[:-lag], y[lag:])[0, 1] if n > lag else 0.0
        correlations[lag] = corr
    return correlations


def main():
    print(f"[{datetime.now():%H:%M:%S}] Granger Causality Engine Started")
    print("=" * 70)

    df = fetch_area_timeseries()
    areas = df["area"].unique()
    print(f"Areas with data: {len(areas)}")
    print(f"Months: {sorted(df['month_year'].unique())}")
    print()

    all_results = []

    for oss_metric, bss_metric, expected_dir in CAUSALITY_PAIRS:
        print(f"\nTesting: {oss_metric} → {bss_metric} (expected: {expected_dir})")
        print("-" * 50)

        area_results = []
        for area in areas:
            area_df = df[df["area"] == area].sort_values("month_idx")
            if len(area_df) < 4:
                continue  # Need at least 4 points for Granger test

            x = area_df[oss_metric]
            y = area_df[bss_metric]

            # Check for constant series
            if x.std() == 0 or y.std() == 0:
                continue

            gc = run_granger_test(x, y, max_lag=MAX_LAG)
            if "error" in gc:
                continue

            xcorr = compute_cross_correlation(x, y, max_lag=MAX_LAG)

            area_results.append({
                "area": area,
                "oss_metric": oss_metric,
                "bss_metric": bss_metric,
                **gc,
                **{f"corr_lag{lag}": v for lag, v in xcorr.items()},
            })

        if not area_results:
            print("  No valid areas for this pair")
            continue

        results_df = pd.DataFrame(area_results)
        n_significant = results_df["significant"].sum()
        n_total = len(results_df)
        mean_best_lag = results_df["best_lag"].mean()
        mean_pvalue = results_df["pvalue"].mean()

        print(f"  Areas tested: {n_total}")
        print(f"  Significant (p<{SIGNIFICANCE_LEVEL}): {n_significant}/{n_total} ({n_significant/n_total*100:.1f}%)")
        print(f"  Mean optimal lag: {mean_best_lag:.2f} months")
        print(f"  Mean p-value: {mean_pvalue:.4f}")
        for lag in range(MAX_LAG + 1):
            col = f"corr_lag{lag}"
            mean_corr = results_df[col].mean()
            print(f"  Mean correlation (lag={lag}): {mean_corr:+.4f}")

        all_results.extend(area_results)

    # Summary
    print("\n" + "=" * 70)
    print("GRANGER CAUSALITY SUMMARY")
    print("=" * 70)
    summary_df = pd.DataFrame(all_results)
    if len(summary_df) > 0:
        for (oss, bss), group in summary_df.groupby(["oss_metric", "bss_metric"]):
            sig_pct = group["significant"].mean() * 100
            mean_lag = group["best_lag"].mean()
            print(f"{oss:>20s} → {bss:<25s} | {sig_pct:5.1f}% significant | lag={mean_lag:.1f}mo")

    # Save results
    out_path = "data/granger_causality_results.csv"
    os.makedirs("data", exist_ok=True)
    summary_df.to_csv(out_path, index=False)
    print(f"\nResults saved to: {out_path}")

    # Save markdown report
    report_path = "data/granger_causality_report.md"
    with open(report_path, "w") as f:
        f.write("# OSS→BSS Granger Causality Report\n\n")
        f.write(f"**Date:** {datetime.now().isoformat()}\n\n")
        f.write("## Methodology\n")
        f.write("- Level: Area-level aggregates\n")
        f.write("- Time span: Jan-May 2026 (5 months)\n")
        f.write("- Test: statsmodels Granger Causality (F-test)\n")
        f.write(f"- Max lag: {MAX_LAG} months\n")
        f.write(f"- Significance: p < {SIGNIFICANCE_LEVEL}\n\n")
        f.write("## Results by Causal Pair\n\n")
        f.write("| OSS Metric | BSS Metric | Areas | Significant % | Mean Lag |\n")
        f.write("|-----------|-----------|-------|--------------|----------|\n")
        if len(summary_df) > 0:
            for (oss, bss), group in summary_df.groupby(["oss_metric", "bss_metric"]):
                sig_pct = group["significant"].mean() * 100
                mean_lag = group["best_lag"].mean()
                n = len(group)
                f.write(f"| {oss} | {bss} | {n} | {sig_pct:.1f}% | {mean_lag:.1f} |\n")
        f.write("\n## Interpretation\n")
        f.write("> **Note:** With only 5 monthly observations, Granger causality tests have low statistical power. ")
        f.write("Results should be interpreted as directional evidence rather than conclusive proof. ")
        f.write("For production deployment, daily or hourly area-level aggregates are recommended.\n")
    print(f"Report saved to: {report_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
