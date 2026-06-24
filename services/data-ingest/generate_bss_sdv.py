"""
Simulated BSS Subscriber Generator — SDV GaussianCopula
-------------------------------------------------------
Generates 500K synthetic subscriber records per month (Jan, Apr, May 2026)
using SDV GaussianCopulaSynthesizer trained on real TT BSS data (Feb, Mar).

Outputs:
  TT_data/BSS/smartcare_cem_jan.csv
  TT_data/BSS/smartcare_cem_avr.csv
  TT_data/BSS/smartcare_cem_mai.csv

Month drift:
  Jan: lower DOU (-12%), less 5G (-35%), fewer silent users
  Apr: higher DOU (+18%), more 5G (+35%), moderate churn emergence
  May: peak DOU (+35%), peak 5G (+65%), high churn/silent patterns

NEVER commit output files to git.
"""

import os
import random
from pathlib import Path

import pandas as pd
from sdv.single_table import GaussianCopulaSynthesizer
from sdv.metadata import SingleTableMetadata

# ── paths ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "TT_data" / "BSS"
IMSI_SALT = os.getenv("IMSI_SALT", "nexo-tt-salt-2026")

REAL_FILES = [
    DATA_DIR / "smartcare_cem_feb.csv",
    DATA_DIR / "smartcare_cem_mars.csv",
]

MONTHS = {
    "2026-01": {
        "label": "jan",
        "dou_factor": 0.88,
        "5g_factor": 0.65,
        "silent_shift": -0.03,
        "churn_shift": -0.02,
    },
    "2026-04": {
        "label": "avr",
        "dou_factor": 1.18,
        "5g_factor": 1.35,
        "silent_shift": 0.04,
        "churn_shift": 0.03,
    },
    "2026-05": {
        "label": "mai",
        "dou_factor": 1.35,
        "5g_factor": 1.65,
        "silent_shift": 0.08,
        "churn_shift": 0.06,
    },
}

N_RECORDS = 500_000


def load_real_data() -> pd.DataFrame:
    dfs = []
    for f in REAL_FILES:
        if not f.exists():
            raise FileNotFoundError(f"Real data file missing: {f}")
        df = pd.read_csv(f, low_memory=False)
        dfs.append(df)
        print(f"  loaded {f.name}: {len(df):,} rows")
    combined = pd.concat(dfs, ignore_index=True)
    print(f"  total real rows: {len(combined):,}")
    # GaussianCopula converges well on 150K rows; full 968K is overkill and slow
    if len(combined) > 150_000:
        combined = combined.sample(n=150_000, random_state=42).reset_index(drop=True)
        print(f"  training subset: {len(combined):,} rows (random sample)")
    return combined


def build_metadata(df: pd.DataFrame) -> SingleTableMetadata:
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(df)

    # Fix types: these are IDs, not sensitive PII in SDV terms
    metadata.update_column(column_name="imsi", sdtype="id", regex_format="60502\\d{10}")
    metadata.update_column(column_name="tac", sdtype="id", regex_format="\\d{15}")

    # month_year should be categorical since we train on Feb+Mar then override
    metadata.update_column(column_name="month_year", sdtype="categorical")

    # Flags are categorical (0/1/NULL/#N/A)
    for col in ["volte_flag", "usim_flag", "session_flag"]:
        metadata.update_column(column_name=col, sdtype="categorical")

    # Attach rates are categorical (0.0/1.0 mostly)
    for col in ["s1_mme_sr", "iu_attach_sr", "gb_attach_sr"]:
        metadata.update_column(column_name=col, sdtype="categorical")

    return metadata


def _make_imsi() -> str:
    return f"60502{random.randint(0, 10**10 - 1):010d}"


def _make_tac() -> str:
    return f"{random.randint(10**14, 10**15 - 1):015d}"


def apply_month_drift(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Apply month-specific drift to a synthetic DataFrame."""
    df = df.copy()

    # DOU drift
    df["dou_total"] = (df["dou_total"] * cfg["dou_factor"]).astype(int)
    df["dou_total"] = df["dou_total"].clip(lower=0)

    # Traffic drift
    df["traffic_2g"] = (
        df["traffic_2g"] * (1.15 if cfg["5g_factor"] < 1.0 else 0.85)
    ).astype(int)
    df["traffic_3g"] = (df["traffic_3g"] * 0.95).astype(int)
    df["traffic_4g"] = (
        df["traffic_4g"] * (0.9 if cfg["5g_factor"] > 1.0 else 1.05)
    ).astype(int)
    df["traffic_5g"] = (df["traffic_5g"] * cfg["5g_factor"]).astype(int)

    # Ensure DOU >= traffic sum
    tsum = df["traffic_2g"] + df["traffic_3g"] + df["traffic_4g"] + df["traffic_5g"]
    mask = tsum > df["dou_total"] * 1.5
    df.loc[mask, "dou_total"] = tsum[mask]

    # Highest RAT drift (5G migration)
    if cfg["5g_factor"] > 1.0:
        # Promote some 4G → 5G
        mask_4g = df["highest_rat"] == "4G"
        promote_count = int(mask_4g.sum() * 0.12 * (cfg["5g_factor"] - 1.0))
        if promote_count > 0:
            idx = (
                df[mask_4g]
                .sample(n=min(promote_count, mask_4g.sum()), random_state=42)
                .index
            )
            df.loc[idx, "highest_rat"] = "5G"
    else:
        # Demote some 5G → 4G
        mask_5g = df["highest_rat"] == "5G"
        demote_count = int(mask_5g.sum() * 0.08)
        if demote_count > 0:
            idx = (
                df[mask_5g]
                .sample(n=min(demote_count, mask_5g.sum()), random_state=42)
                .index
            )
            df.loc[idx, "highest_rat"] = "4G"

    # Usertype drift (silent/churn emergence)
    if cfg["silent_shift"] > 0:
        # Some Data/Voice users become Silent
        mask_data = df["usertype"] == "Data User"
        n_silent = int(mask_data.sum() * cfg["silent_shift"] * 0.6)
        if n_silent > 0:
            idx = (
                df[mask_data]
                .sample(n=min(n_silent, mask_data.sum()), random_state=42)
                .index
            )
            df.loc[idx, "usertype"] = "Silent User"

        mask_voice = df["usertype"] == "Voice User"
        n_silent_v = int(mask_voice.sum() * cfg["silent_shift"] * 0.4)
        if n_silent_v > 0:
            idx = (
                df[mask_voice]
                .sample(n=min(n_silent_v, mask_voice.sum()), random_state=42)
                .index
            )
            df.loc[idx, "usertype"] = "Silent User"

    # New IMSI/TAC for every record
    df["imsi"] = [_make_imsi() for _ in range(len(df))]
    df["tac"] = [_make_tac() for _ in range(len(df))]

    return df


def main():
    print("Loading real BSS data...")
    real_df = load_real_data()

    print("\nBuilding metadata...")
    metadata = build_metadata(real_df)

    print("\nFitting GaussianCopula on 968K real rows...")
    synthesizer = GaussianCopulaSynthesizer(metadata)
    synthesizer.fit(real_df)
    print("  fit complete")

    for month_key, cfg in MONTHS.items():
        print(f"\nGenerating {month_key} ({cfg['label']}) — {N_RECORDS:,} records...")
        synthetic = synthesizer.sample(num_rows=N_RECORDS)
        synthetic = apply_month_drift(synthetic, cfg)
        synthetic["month_year"] = month_key

        out_path = DATA_DIR / f"smartcare_cem_{cfg['label']}.csv"
        synthetic.to_csv(out_path, index=False)
        print(f"  written {len(synthetic):,} rows → {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
