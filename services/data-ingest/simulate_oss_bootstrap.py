"""
Bootstrap OSS Simulation — Jan / Feb / May / Jun
------------------------------------------------
Generates simulated OSS KPIs by bootstrap-sampling from REAL OSS data.
Same methodology as BSS month generation:
  1. Stratified bootstrap sampling from 18.8M real OSS rows
  2. Log-normal perturbation on numerical columns
  3. Month drift (slight KPI shifts per month)
  4. New cell_id assignment per record

Target: ~50K rows/month (200K total) — sufficient for training diversity
without overwhelming the real data distribution.
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel")
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

MONTHS = {
    "2026-01": {"days": 31, "drift": -0.08},   # Jan: lower activity
    "2026-02": {"days": 28, "drift": -0.03},   # Feb: slightly lower
    "2026-05": {"days": 31, "drift": +0.05},   # May: higher activity
    "2026-06": {"days": 30, "drift": +0.10},   # Jun: peak activity
    "2026-07": {"days": 31, "drift": +0.12},   # Jul: peak summer heat strain
    "2026-08": {"days": 31, "drift": +0.10},   # Aug: sustained peak
    "2026-09": {"days": 30, "drift": +0.03},   # Sep: post-summer recovery
}
SAMPLES_PER_MONTH = 50_000
NUMERICAL_COLS = ["throughput_mbps", "latency_ms", "packet_loss_rate", 
                  "jitter_ms", "active_users", "rsrp_dbm", "cell_load_pct"]


def get_conn():
    return psycopg2.connect(DB_URL)


def fetch_real_oss_sample(n: int) -> pd.DataFrame:
    """Fetch stratified random sample from real OSS data."""
    print(f"[bootstrap-oss] Fetching {n:,} real OSS rows for bootstrap reservoir...")
    sql = """
        SELECT cell_id, area, rat_type, throughput_mbps, latency_ms,
               packet_loss_rate, jitter_ms, active_users, rsrp_dbm,
               cell_load_pct, anomaly_flag, integrity, call_drop_rate, site_name
        FROM oss_cell_kpis
        WHERE source = 'real'
        ORDER BY RANDOM()
        LIMIT %s
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn, params=(n,))
    print(f"  ... loaded {len(df):,} real rows")
    return df


def bootstrap_month(reservoir: pd.DataFrame, month_year: str, drift: float) -> list[tuple]:
    """Generate one simulated month via bootstrap + perturbation."""
    print(f"[bootstrap-oss] Generating {month_year} (drift={drift:+.2f})...")
    rng = np.random.default_rng(seed=int(month_year.replace("-", "")))
    
    # Bootstrap sample with replacement
    n = SAMPLES_PER_MONTH
    sampled = reservoir.sample(n=n, replace=True, random_state=rng.integers(0, 2**31))
    
    # Log-normal perturbation on numerical columns
    for col in NUMERICAL_COLS:
        if col in sampled.columns:
            # Multiplicative perturbation: x * exp(N(0, 0.06))
            noise = rng.lognormal(mean=0.0, sigma=0.06, size=n)
            sampled[col] = sampled[col] * noise
    
    # Month drift: shift all numerical KPIs by drift factor
    for col in NUMERICAL_COLS:
        if col in sampled.columns:
            if col in ["throughput_mbps", "active_users", "rsrp_dbm"]:
                sampled[col] = sampled[col] * (1 + drift)
            elif col in ["latency_ms", "packet_loss_rate", "jitter_ms", "cell_load_pct"]:
                sampled[col] = sampled[col] * (1 - drift)  # inverse: worse network = lower quality
    
    # Regenerate timestamps uniformly across the month
    base_date = datetime.strptime(month_year, "%Y-%m")
    days_in_month = MONTHS[month_year]["days"]
    timestamps = [base_date + timedelta(days=int(rng.integers(0, days_in_month)), 
                                        hours=int(rng.integers(0, 24))) for _ in range(n)]
    
    # New cell_id per record (to avoid collisions)
    sampled["cell_id"] = [f"SIM{month_year.replace('-','')}{i:06d}" for i in range(n)]
    sampled["timestamp"] = timestamps
    sampled["month_year"] = month_year
    sampled["source"] = "simulated"
    
    # Recompute anomaly flag based on real criteria
    sampled["anomaly_flag"] = (
        (sampled["integrity"] < 100.0) | 
        (sampled["call_drop_rate"] > 2.0)
    )
    
    # Build rows for INSERT
    rows = []
    for _, row in sampled.iterrows():
        rows.append((
            row["cell_id"], row["area"], row["month_year"],
            round(row["throughput_mbps"], 2) if pd.notna(row["throughput_mbps"]) else None,
            round(row["latency_ms"], 2) if pd.notna(row["latency_ms"]) else None,
            round(row["packet_loss_rate"], 4) if pd.notna(row["packet_loss_rate"]) else None,
            round(row["jitter_ms"], 2) if pd.notna(row["jitter_ms"]) else None,
            int(row["active_users"]) if pd.notna(row["active_users"]) else None,
            round(row["rsrp_dbm"], 1) if pd.notna(row["rsrp_dbm"]) else None,
            round(row["cell_load_pct"], 2) if pd.notna(row["cell_load_pct"]) else None,
            bool(row["anomaly_flag"]),
            row["rat_type"],
            round(row["integrity"], 2) if pd.notna(row["integrity"]) else None,
            round(row["call_drop_rate"], 4) if pd.notna(row["call_drop_rate"]) else None,
            row["timestamp"].isoformat(),
            row["site_name"],
            row["source"],
        ))
    
    print(f"  ... {len(rows):,} rows generated, anomaly rate: {sampled['anomaly_flag'].mean()*100:.1f}%")
    return rows


def insert_rows(rows: list[tuple]):
    sql = """
        INSERT INTO oss_cell_kpis (
            cell_id, area, month_year, throughput_mbps, latency_ms,
            packet_loss_rate, jitter_ms, active_users, rsrp_dbm,
            cell_load_pct, anomaly_flag, rat_type, integrity,
            call_drop_rate, timestamp, site_name, source
        ) VALUES %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        conn.commit()


def main():
    print("=" * 60)
    print("Bootstrap OSS Simulation from Real Data")
    print("=" * 60)
    
    # Build reservoir from real data
    reservoir = fetch_real_oss_sample(n=200_000)
    
    for month, cfg in MONTHS.items():
        rows = bootstrap_month(reservoir, month, cfg["drift"])
        insert_rows(rows)
    
    # Verify
    with get_conn() as conn:
        df_check = pd.read_sql(
            "SELECT month_year, source, COUNT(*) FROM oss_cell_kpis GROUP BY month_year, source ORDER BY month_year",
            conn
        )
    print("\n[done] Final OSS counts:")
    print(df_check.to_string(index=False))


if __name__ == "__main__":
    main()
