#!/usr/bin/env python3
"""
Consistent BSS Subscriber Generator — Identity-Preserving Multi-Month Simulation
-------------------------------------------------------------------------------
Generates Jan, Apr, May 2026 simulated BSS data using REAL subscriber identities
from Feb/Mar so subscribers appear consistently across months for LSTM churn training.

- Jan uses ONLY Feb identities (backward temporal drift)
- Apr uses ONLY Mar identities (forward drift)
- May uses ONLY Mar identities (stronger forward drift)
- Each subscriber keeps the same imsi_hash across months
- Features perturbed with log-normal noise + month drift
- churned flag: 5-8% randomly assigned per month

Outputs:
  TT_data/BSS/smartcare_cem_jan_consistent.csv
  TT_data/BSS/smartcare_cem_avr_consistent.csv
  TT_data/BSS/smartcare_cem_mai_consistent.csv

NEVER commit output files to git.
"""

import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ── config ───────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "TT_data" / "BSS"

FEB_FILE = DATA_DIR / "smartcare_cem_feb.csv"
MAR_FILE = DATA_DIR / "smartcare_cem_mars.csv"

MONTHS = {
    "2026-01": {
        "label": "jan",
        "source_file": FEB_FILE,
        "dou_factor": 0.88,
        "5g_factor": 0.65,
        "silent_shift": -0.03,
        "demote_5g_pct": 0.08,
        "promote_4g_pct": 0.0,
        "churn_rate": 0.05,
    },
    "2026-04": {
        "label": "avr",
        "source_file": MAR_FILE,
        "dou_factor": 1.18,
        "5g_factor": 1.35,
        "silent_shift": 0.04,
        "demote_5g_pct": 0.0,
        "promote_4g_pct": 0.12,
        "churn_rate": 0.07,
    },
    "2026-05": {
        "label": "mai",
        "source_file": MAR_FILE,
        "dou_factor": 1.35,
        "5g_factor": 1.65,
        "silent_shift": 0.08,
        "demote_5g_pct": 0.0,
        "promote_4g_pct": 0.12,
        "churn_rate": 0.08,
    },
    "2026-06": {
        "label": "jun",
        "source_file": MAR_FILE,
        "dou_factor": 1.45,
        "5g_factor": 1.80,
        "silent_shift": 0.10,
        "demote_5g_pct": 0.0,
        "promote_4g_pct": 0.15,
        "churn_rate": 0.085,
    },
    "2026-07": {
        "label": "jul",
        "source_file": MAR_FILE,
        "dou_factor": 1.55,
        "5g_factor": 1.95,
        "silent_shift": 0.12,
        "demote_5g_pct": 0.0,
        "promote_4g_pct": 0.18,
        "churn_rate": 0.09,
    },
    "2026-08": {
        "label": "aou",
        "source_file": MAR_FILE,
        "dou_factor": 1.50,
        "5g_factor": 1.90,
        "silent_shift": 0.11,
        "demote_5g_pct": 0.0,
        "promote_4g_pct": 0.16,
        "churn_rate": 0.095,
    },
    "2026-09": {
        "label": "sep",
        "source_file": MAR_FILE,
        "dou_factor": 1.30,
        "5g_factor": 1.60,
        "silent_shift": 0.06,
        "demote_5g_pct": 0.0,
        "promote_4g_pct": 0.10,
        "churn_rate": 0.08,
    },
}

N_RECORDS = 500_000
BATCH_SIZE = 5_000
RNG = np.random.default_rng(42)

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel",
)
IMSI_SALT = os.getenv("IMSI_SALT", "nexo-tt-salt-2026")


# ── helpers ──────────────────────────────────────────────────────────────────


def get_conn():
    return psycopg2.connect(DB_URL)


def hash_imsi(imsi: str) -> str:
    return hashlib.sha256(f"{imsi}{IMSI_SALT}".encode()).hexdigest()[:32]


def load_source_data(filepath: Path) -> pd.DataFrame:
    if not filepath.exists():
        raise FileNotFoundError(f"Real data file missing: {filepath}")
    df = pd.read_csv(filepath, low_memory=False)
    n_unique = df["imsi"].nunique()
    print(f"  loaded {filepath.name}: {len(df):,} rows, {n_unique:,} unique identities")
    return df


def perturb_numerical(df: pd.DataFrame) -> pd.DataFrame:
    """Add log-normal noise to numerical columns."""
    num_cols = [
        "dou_total",
        "traffic_2g",
        "traffic_3g",
        "traffic_4g",
        "traffic_5g",
        "duration",
        "voice_onlinetime_3g",
        "voice_onlinetime_2g",
    ]
    for col in num_cols:
        if col in df.columns:
            noise = np.exp(RNG.normal(0, 0.06, len(df)))
            df[col] = (df[col].astype(float) * noise).round().astype(int)
            df[col] = df[col].clip(lower=0)
    return df


def apply_month_drift(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Apply month-specific drift to features."""
    df = df.copy()

    # DOU drift
    df["dou_total"] = (df["dou_total"] * cfg["dou_factor"]).round().astype(int)
    df["dou_total"] = df["dou_total"].clip(lower=0)

    # Traffic drift
    df["traffic_2g"] = (
        df["traffic_2g"] * (1.15 if cfg["5g_factor"] < 1.0 else 0.85)
    ).round().astype(int)
    df["traffic_3g"] = (df["traffic_3g"] * 0.95).round().astype(int)
    df["traffic_4g"] = (
        df["traffic_4g"] * (0.9 if cfg["5g_factor"] > 1.0 else 1.05)
    ).round().astype(int)
    df["traffic_5g"] = (df["traffic_5g"] * cfg["5g_factor"]).round().astype(int)
    df["traffic_5g"] = df["traffic_5g"].clip(lower=0)

    # Ensure DOU >= traffic sum (cap at 1.5x)
    tsum = (
        df["traffic_2g"]
        + df["traffic_3g"]
        + df["traffic_4g"]
        + df["traffic_5g"]
    )
    mask = tsum > df["dou_total"] * 1.5
    df.loc[mask, "dou_total"] = tsum[mask]

    # Highest RAT drift
    if cfg.get("promote_4g_pct", 0) > 0:
        mask_4g = df["highest_rat"] == "4G"
        n = int(mask_4g.sum() * cfg["promote_4g_pct"])
        if n > 0:
            idx = (
                df[mask_4g]
                .sample(n=min(n, mask_4g.sum()), random_state=42)
                .index
            )
            df.loc[idx, "highest_rat"] = "5G"
    elif cfg.get("demote_5g_pct", 0) > 0:
        mask_5g = df["highest_rat"] == "5G"
        n = int(mask_5g.sum() * cfg["demote_5g_pct"])
        if n > 0:
            idx = (
                df[mask_5g]
                .sample(n=min(n, mask_5g.sum()), random_state=42)
                .index
            )
            df.loc[idx, "highest_rat"] = "4G"

    # Silent user drift
    silent_shift = cfg.get("silent_shift", 0)
    if silent_shift > 0:
        # Data/Voice -> Silent
        mask_d = df["usertype"] == "Data User"
        n = int(mask_d.sum() * silent_shift * 0.6)
        if n > 0:
            idx = (
                df[mask_d]
                .sample(n=min(n, mask_d.sum()), random_state=43)
                .index
            )
            df.loc[idx, "usertype"] = "Silent User"
        mask_v = df["usertype"] == "Voice User"
        n = int(mask_v.sum() * silent_shift * 0.4)
        if n > 0:
            idx = (
                df[mask_v]
                .sample(n=min(n, mask_v.sum()), random_state=44)
                .index
            )
            df.loc[idx, "usertype"] = "Silent User"
    elif silent_shift < 0:
        # Silent -> Data/Voice (reverse drift)
        mask_s = df["usertype"] == "Silent User"
        n = int(mask_s.sum() * abs(silent_shift))
        if n > 0:
            idx = (
                df[mask_s]
                .sample(n=min(n, mask_s.sum()), random_state=45)
                .index
            )
            split = int(len(idx) * 0.6)
            df.loc[idx[:split], "usertype"] = "Data User"
            df.loc[idx[split:], "usertype"] = "Voice User"

    # churned flag: 5-8% random per month (with small jitter)
    actual_rate = float(
        np.clip(cfg.get("churn_rate", 0.065) + RNG.normal(0, 0.005), 0.05, 0.08)
    )
    df["churned"] = RNG.random(len(df)) < actual_rate

    return df


def generate_month(source_df: pd.DataFrame, month_key: str) -> pd.DataFrame:
    """Generate a full simulated month from source data, preserving identities."""
    cfg = MONTHS[month_key]
    label = cfg["label"]
    print(
        f"\nGenerating {month_key} ({label}) — {N_RECORDS:,} records from {cfg['source_file'].name}..."
    )

    # Sample with replacement from source (required when source < 500K)
    sampled = source_df.sample(
        n=N_RECORDS, replace=True, random_state=42
    ).reset_index(drop=True)

    # Apply perturbations
    sampled = perturb_numerical(sampled.copy())
    sampled = apply_month_drift(sampled, cfg)

    # Update month_year
    sampled["month_year"] = month_key

    # Ensure column order matches original + churned
    base_cols = [
        "imsi",
        "tac",
        "model",
        "brand",
        "tertype",
        "generation",
        "sim_slot",
        "volte_flag",
        "usim_flag",
        "area",
        "area_delegation",
        "usertype",
        "dou_total",
        "traffic_2g",
        "traffic_3g",
        "traffic_4g",
        "traffic_5g",
        "duration",
        "voice_onlinetime_3g",
        "voice_onlinetime_2g",
        "s1_mme_sr",
        "iu_attach_sr",
        "gb_attach_sr",
        "session_flag",
        "highest_rat",
        "month_year",
        "churned",
    ]

    for col in base_cols:
        if col not in sampled.columns:
            sampled[col] = None

    out_df = sampled[base_cols]
    out_path = DATA_DIR / f"smartcare_cem_{label}_consistent.csv"
    out_df.to_csv(out_path, index=False)
    print(
        f"  written → {out_path} ({len(out_df):,} rows, "
        f"{out_df['imsi'].nunique():,} unique identities, "
        f"{out_df['churned'].sum():,} churned)"
    )

    return out_df


# ── database operations ──────────────────────────────────────────────────────


def ensure_churned_column():
    """Add churned column to bss_subscribers and subscriber_features if missing."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE bss_subscribers
                ADD COLUMN IF NOT EXISTS churned BOOLEAN DEFAULT FALSE
                """
            )
            cur.execute(
                """
                ALTER TABLE subscriber_features
                ADD COLUMN IF NOT EXISTS churned BOOLEAN DEFAULT FALSE
                """
            )
        conn.commit()
    print("[db] Ensured churned column exists in bss_subscribers and subscriber_features")


def delete_old_simulated_bss() -> int:
    """Delete old simulated BSS rows for all simulated months."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM bss_subscribers
                WHERE month_year IN ('2026-01', '2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09')
                """
            )
            deleted = cur.rowcount
        conn.commit()
    print(f"[db] Deleted {deleted:,} old simulated BSS rows")
    return deleted


def _to_db_value(value, typ=int):
    """Safely coerce a pandas value to a DB-friendly Python scalar."""
    if pd.isna(value):
        return None
    try:
        return typ(value)
    except (ValueError, TypeError):
        return None


def df_rows_to_db(df: pd.DataFrame) -> list[tuple]:
    """Convert DataFrame rows to DB tuples matching bss_subscribers schema + churned."""
    rows = []
    for _, r in df.iterrows():
        imsi_hash = hash_imsi(str(r["imsi"]))
        rows.append(
            (
                imsi_hash,
                r.get("tac") or None,
                r.get("model") or None,
                r.get("brand") or None,
                r.get("tertype") or None,
                r.get("generation") or None,
                r.get("sim_slot") or None,
                _to_db_value(r.get("volte_flag"), int),
                _to_db_value(r.get("usim_flag"), int),
                r.get("area") or None,
                r.get("area_delegation") or None,
                r.get("usertype") or None,
                _to_db_value(r.get("dou_total"), int),
                _to_db_value(r.get("traffic_2g"), int),
                _to_db_value(r.get("traffic_3g"), int),
                _to_db_value(r.get("traffic_4g"), int),
                _to_db_value(r.get("traffic_5g"), int),
                _to_db_value(r.get("duration"), float),
                _to_db_value(r.get("voice_onlinetime_3g"), float),
                _to_db_value(r.get("voice_onlinetime_2g"), float),
                _to_db_value(r.get("s1_mme_sr"), float),
                _to_db_value(r.get("iu_attach_sr"), float),
                _to_db_value(r.get("gb_attach_sr"), float),
                _to_db_value(r.get("session_flag"), int),
                r.get("highest_rat") or None,
                r.get("month_year") or None,
                bool(r["churned"]) if pd.notna(r.get("churned")) else False,
            )
        )
    return rows


def insert_bss_df(df: pd.DataFrame, batch_size: int = BATCH_SIZE) -> int:
    """Insert a BSS DataFrame into PostgreSQL, deduplicating by imsi within the month."""
    # Deduplicate by imsi within this DataFrame (same month) to respect
    # UNIQUE(imsi_hash, month_year). Keep first occurrence.
    before_dedup = len(df)
    df_unique = df.drop_duplicates(subset=["imsi"], keep="first")
    after_dedup = len(df_unique)
    if after_dedup < before_dedup:
        print(
            f"  deduplicated {before_dedup - after_dedup:,} duplicate imsi "
            f"(keep {after_dedup:,} unique)"
        )

    sql = """
        INSERT INTO bss_subscribers (
            imsi_hash, tac, model, brand, tertype, generation, sim_slot,
            volte_flag, usim_flag, area, area_delegation, usertype,
            dou_total, traffic_2g, traffic_3g, traffic_4g, traffic_5g,
            duration, voice_onlinetime_3g, voice_onlinetime_2g,
            s1_mme_sr, iu_attach_sr, gb_attach_sr,
            session_flag, highest_rat, month_year, churned
        ) VALUES %s
        ON CONFLICT (imsi_hash, month_year) DO UPDATE SET
            tac = EXCLUDED.tac,
            model = EXCLUDED.model,
            brand = EXCLUDED.brand,
            tertype = EXCLUDED.tertype,
            generation = EXCLUDED.generation,
            sim_slot = EXCLUDED.sim_slot,
            volte_flag = EXCLUDED.volte_flag,
            usim_flag = EXCLUDED.usim_flag,
            area = EXCLUDED.area,
            area_delegation = EXCLUDED.area_delegation,
            usertype = EXCLUDED.usertype,
            dou_total = EXCLUDED.dou_total,
            traffic_2g = EXCLUDED.traffic_2g,
            traffic_3g = EXCLUDED.traffic_3g,
            traffic_4g = EXCLUDED.traffic_4g,
            traffic_5g = EXCLUDED.traffic_5g,
            duration = EXCLUDED.duration,
            voice_onlinetime_3g = EXCLUDED.voice_onlinetime_3g,
            voice_onlinetime_2g = EXCLUDED.voice_onlinetime_2g,
            s1_mme_sr = EXCLUDED.s1_mme_sr,
            iu_attach_sr = EXCLUDED.iu_attach_sr,
            gb_attach_sr = EXCLUDED.gb_attach_sr,
            session_flag = EXCLUDED.session_flag,
            highest_rat = EXCLUDED.highest_rat,
            churned = EXCLUDED.churned
    """
    rows = df_rows_to_db(df_unique)
    total = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                execute_values(cur, sql, batch)
                total += len(batch)
                print(f"  ... {total:,} / {len(rows):,} rows inserted/updated")
        conn.commit()
    return total


def recompute_features():
    """Re-run feature computation for affected months."""
    ingest_dir = str(PROJECT_ROOT / "services" / "data-ingest")
    if ingest_dir not in sys.path:
        sys.path.insert(0, ingest_dir)
    import compute_features as cf

    for month in ["2026-01", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]:
        cf.compute_features_for_month(month)
    print("\n[done] Feature recomputation complete")


# ── main ─────────────────────────────────────────────────────────────────────


def main():
    print("=" * 70)
    print("Consistent BSS Month Generator (Identity-Preserving)")
    print("=" * 70)

    # Load source data
    print("\nLoading real BSS data...")
    feb_df = load_source_data(FEB_FILE)
    mar_df = load_source_data(MAR_FILE)

    # Ensure DB schema is ready
    ensure_churned_column()

    # Generate months
    jan_df = generate_month(feb_df, "2026-01")
    apr_df = generate_month(mar_df, "2026-04")
    may_df = generate_month(mar_df, "2026-05")
    jun_df = generate_month(mar_df, "2026-06")
    jul_df = generate_month(mar_df, "2026-07")
    aug_df = generate_month(mar_df, "2026-08")
    sep_df = generate_month(mar_df, "2026-09")

    # Delete old simulated data
    print("\n[db] Cleaning old simulated BSS data...")
    delete_old_simulated_bss()

    # Insert new consistent data
    print("\n[db] Inserting consistent simulated BSS data...")
    total_inserted = 0
    for df, label in [(jan_df, "jan"), (apr_df, "avr"), (may_df, "mai"),
                        (jun_df, "jun"), (jul_df, "jul"), (aug_df, "aou"), (sep_df, "sep")]:
        print(f"  Inserting {label} ...")
        total_inserted += insert_bss_df(df)

    print(f"\n[db] Total rows inserted/updated: {total_inserted:,}")

    # Recompute features
    print("\n[features] Recomputing subscriber features and area health...")
    recompute_features()

    print("\n" + "=" * 70)
    print("All done. Consistent simulated BSS months generated and ingested.")
    print("=" * 70)


if __name__ == "__main__":
    main()
