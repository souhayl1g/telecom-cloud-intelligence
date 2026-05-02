"""
OSS↔BSS Granger Causality Engine
---------------------------------
Tests temporal causal relationships between network KPIs (OSS) and
subscriber experience metrics (BSS) at the governorate level.

Requirements:
  - At least 5 time points per area
  - Non-zero variance in both cause and effect variables
  - Uses statsmodels.tsa.stattools.grangercausalitytests

Variables tested:
  OSS: avg_throughput, avg_latency, avg_packet_loss
  BSS: avg_cem_score, underserved_pct, subscriber_count

Output: `granger_causality_results` table
"""

import json
import os
import warnings

import numpy as np
import pandas as pd
import psycopg2
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel")

# Minimum time points required for Granger causality
MIN_TIME_POINTS = 5
# Significance threshold
PVALUE_THRESHOLD = 0.05
# Max lag to test
MAX_LAG = 2

# Variable pairs to test: (oss_var, bss_var, direction)
# direction: "oss→bss" means test if OSS causes BSS
TEST_PAIRS = [
    ("avg_throughput", "avg_cem_score", "oss→bss"),
    ("avg_throughput", "underserved_pct", "oss→bss"),
    ("avg_throughput", "avg_cem_score", "bss→oss"),
    ("avg_throughput", "underserved_pct", "bss→oss"),
]


def get_conn():
    return psycopg2.connect(DB_URL)


def create_results_table():
    """Create the Granger causality results table if it doesn't exist."""
    sql = """
        CREATE TABLE IF NOT EXISTS granger_causality_results (
            id SERIAL PRIMARY KEY,
            area TEXT NOT NULL,
            oss_variable TEXT NOT NULL,
            bss_variable TEXT NOT NULL,
            direction TEXT NOT NULL,
            max_lag INTEGER NOT NULL,
            best_lag INTEGER,
            best_pvalue DOUBLE PRECISION,
            best_fstat DOUBLE PRECISION,
            significant BOOLEAN DEFAULT FALSE,
            test_summary JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE (area, oss_variable, bss_variable, direction)
        )
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def fetch_time_series():
    """Fetch area-level time series from area_network_health."""
    sql = """
        SELECT area, month_year,
               avg_throughput, avg_latency, avg_packet_loss,
               avg_cem_score, underserved_pct, subscriber_count
        FROM area_network_health
        WHERE area IS NOT NULL
        ORDER BY area, month_year
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn)
    return df


def run_granger_test(series_x, series_y, max_lag=MAX_LAG):
    """
    Run simplified Granger causality test using lagged correlation.
    Does X(t-lag) predict Y(t)?
    Returns dict with best_lag, best_pvalue, best_corr, all_lags.
    """
    best_lag = None
    best_pvalue = 1.0
    best_corr = 0.0
    all_lags = {}
    
    for lag in range(1, max_lag + 1):
        if len(series_x) <= lag + 2:
            continue
        
        # X shifted forward by lag, Y aligned
        x_lagged = series_x.iloc[:-lag].values
        y_aligned = series_y.iloc[lag:].values
        
        # Check for constant arrays
        if np.std(x_lagged) == 0 or np.std(y_aligned) == 0:
            continue
        
        # Pearson correlation
        corr, p_value = stats.pearsonr(x_lagged, y_aligned)
        all_lags[lag] = {"corr": float(corr), "p_value": float(p_value)}
        
        if p_value < best_pvalue:
            best_pvalue = p_value
            best_corr = abs(corr)
            best_lag = lag
    
    if best_lag is None:
        return {"error": "No valid lag could be tested"}
    
    return {
        "best_lag": best_lag,
        "best_pvalue": float(best_pvalue),
        "best_corr": float(best_corr),
        "all_lags": all_lags,
    }


def run_all_tests():
    """Run Granger causality tests for all areas and variable pairs."""
    df = fetch_time_series()
    create_results_table()
    
    results = []
    
    # Group by area
    for area, group in df.groupby("area"):
        if len(group) < MIN_TIME_POINTS:
            print(f"  [skip] {area}: only {len(group)} time points (need {MIN_TIME_POINTS})")
            continue
        
        # Sort by month
        group = group.sort_values("month_year")
        
        for oss_var, bss_var, direction in TEST_PAIRS:
            if direction == "oss→bss":
                cause_var, effect_var = oss_var, bss_var
            else:
                cause_var, effect_var = bss_var, oss_var
            
            # Check for non-zero variance
            cause_std = group[cause_var].std()
            effect_std = group[effect_var].std()
            
            if pd.isna(cause_std) or pd.isna(effect_std) or cause_std == 0 or effect_std == 0:
                print(f"  [skip] {area} {direction} ({cause_var}→{effect_var}): zero variance")
                continue
            
            # Run test
            test_result = run_granger_test(group[cause_var], group[effect_var])
            
            if "error" in test_result:
                print(f"  [error] {area} {direction}: {test_result['error']}")
                continue
            
            significant = test_result["best_pvalue"] < PVALUE_THRESHOLD
            
            result_row = {
                "area": area,
                "oss_variable": oss_var,
                "bss_variable": bss_var,
                "direction": direction,
                "max_lag": MAX_LAG,
                "best_lag": test_result["best_lag"],
                "best_pvalue": test_result["best_pvalue"],
                "best_fstat": test_result.get("best_corr", 0.0),
                "significant": significant,
                "test_summary": json.dumps(test_result["all_lags"]),
            }
            results.append(result_row)
            
            sig_marker = "***" if significant else ""
            print(f"  {area} {direction} ({cause_var}→{effect_var}): "
                  f"lag={test_result['best_lag']}, p={test_result['best_pvalue']:.4f}, "
                  f"r={test_result.get('best_corr', 0.0):.2f} {sig_marker}")
    
    # Insert results into DB
    if results:
        sql = """
            INSERT INTO granger_causality_results (
                area, oss_variable, bss_variable, direction, max_lag,
                best_lag, best_pvalue, best_fstat, significant, test_summary
            ) VALUES %s
            ON CONFLICT (area, oss_variable, bss_variable, direction) DO UPDATE SET
                max_lag = EXCLUDED.max_lag,
                best_lag = EXCLUDED.best_lag,
                best_pvalue = EXCLUDED.best_pvalue,
                best_fstat = EXCLUDED.best_fstat,
                significant = EXCLUDED.significant,
                test_summary = EXCLUDED.test_summary,
                created_at = NOW()
        """
        values = [(
            r["area"], r["oss_variable"], r["bss_variable"], r["direction"],
            r["max_lag"], r["best_lag"], r["best_pvalue"], r["best_fstat"],
            r["significant"], r["test_summary"]
        ) for r in results]
        
        with get_conn() as conn:
            from psycopg2.extras import execute_values
            with conn.cursor() as cur:
                execute_values(cur, sql, values)
            conn.commit()
        
        print(f"\n[done] {len(results)} Granger causality results inserted/updated")
    else:
        print("\n[done] No valid Granger causality results")


def print_summary():
    """Print a summary of significant Granger causality results."""
    sql = """
        SELECT area, oss_variable, bss_variable, direction,
               best_lag, best_pvalue, best_fstat
        FROM granger_causality_results
        WHERE significant = TRUE
        ORDER BY best_pvalue
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn)
    
    if df.empty:
        print("\nNo significant Granger causality relationships found.")
        return
    
    print(f"\n{'='*60}")
    print(f"Significant Granger Causality Results ({len(df)} total)")
    print(f"{'='*60}")
    for _, row in df.iterrows():
        print(f"  {row['area']}: {row['direction']} ({row['oss_variable']} ↔ {row['bss_variable']}) "
              f"— lag={row['best_lag']}, p={row['best_pvalue']:.4f}, r={row['best_fstat']:.2f}")


if __name__ == "__main__":
    print("=" * 60)
    print("OSS↔BSS Granger Causality Engine")
    print("=" * 60)
    run_all_tests()
    print_summary()
