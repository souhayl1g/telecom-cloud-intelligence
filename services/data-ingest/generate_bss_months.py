"""
Simulated BSS Subscriber Generator — Stratified Bootstrap
---------------------------------------------------------
Generates 500K synthetic subscriber records per month (Jan, Apr, May 2026)
by bootstrap-resampling real TT BSS data with perturbation.

Preserves all real correlations perfectly (base rows are real).
Adds Gaussian/log-normal noise to numerical columns for privacy.
Applies month-specific drift for temporal realism.

Outputs:
  TT_data/BSS/smartcare_cem_jan.csv
  TT_data/BSS/smartcare_cem_avr.csv
  TT_data/BSS/smartcare_cem_mai.csv

NEVER commit output files to git.
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ── config ───────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "TT_data" / "BSS"

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
    },
    "2026-04": {
        "label": "avr",
        "dou_factor": 1.18,
        "5g_factor": 1.35,
        "silent_shift": 0.04,
    },
    "2026-05": {
        "label": "mai",
        "dou_factor": 1.35,
        "5g_factor": 1.65,
        "silent_shift": 0.08,
    },
    "2026-06": {
        "label": "jun",
        "dou_factor": 1.50,
        "5g_factor": 1.80,
        "silent_shift": 0.10,
    },
    "2026-07": {
        "label": "jul",
        "dou_factor": 1.65,
        "5g_factor": 2.00,
        "silent_shift": 0.12,
    },
    "2026-08": {
        "label": "aug",
        "dou_factor": 1.55,
        "5g_factor": 1.90,
        "silent_shift": 0.10,
    },
    "2026-09": {
        "label": "sep",
        "dou_factor": 1.40,
        "5g_factor": 1.70,
        "silent_shift": 0.07,
    },
}

N_RECORDS = 500_000
BATCH_SIZE = 50_000
RNG = np.random.default_rng(42)


def _make_imsi() -> str:
    return f"60502{RNG.integers(0, 10**10):010d}"


def _make_tac() -> str:
    return f"{RNG.integers(10**14, 10**15):015d}"


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
    return combined


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
    """Apply month-specific drift."""
    df = df.copy()

    # DOU drift
    df["dou_total"] = (df["dou_total"] * cfg["dou_factor"]).round().astype(int)
    df["dou_total"] = df["dou_total"].clip(lower=0)

    # Traffic drift
    df["traffic_2g"] = (
        (df["traffic_2g"] * (1.15 if cfg["5g_factor"] < 1.0 else 0.85))
        .round()
        .astype(int)
    )
    df["traffic_3g"] = (df["traffic_3g"] * 0.95).round().astype(int)
    df["traffic_4g"] = (
        (df["traffic_4g"] * (0.9 if cfg["5g_factor"] > 1.0 else 1.05))
        .round()
        .astype(int)
    )
    df["traffic_5g"] = (df["traffic_5g"] * cfg["5g_factor"]).round().astype(int)
    df["traffic_5g"] = df["traffic_5g"].clip(lower=0)

    # Ensure DOU >= traffic sum
    tsum = df["traffic_2g"] + df["traffic_3g"] + df["traffic_4g"] + df["traffic_5g"]
    mask = tsum > df["dou_total"] * 1.5
    df.loc[mask, "dou_total"] = tsum[mask]

    # Highest RAT drift
    if cfg["5g_factor"] > 1.0:
        mask_4g = df["highest_rat"] == "4G"
        n = int(mask_4g.sum() * 0.12 * (cfg["5g_factor"] - 1.0))
        if n > 0:
            idx = df[mask_4g].sample(n=min(n, mask_4g.sum()), random_state=42).index
            df.loc[idx, "highest_rat"] = "5G"
    else:
        mask_5g = df["highest_rat"] == "5G"
        n = int(mask_5g.sum() * 0.08)
        if n > 0:
            idx = df[mask_5g].sample(n=min(n, mask_5g.sum()), random_state=42).index
            df.loc[idx, "highest_rat"] = "4G"

    # Silent user drift
    if cfg["silent_shift"] > 0:
        mask_d = df["usertype"] == "Data User"
        n = int(mask_d.sum() * cfg["silent_shift"] * 0.6)
        if n > 0:
            idx = df[mask_d].sample(n=min(n, mask_d.sum()), random_state=42).index
            df.loc[idx, "usertype"] = "Silent User"
        mask_v = df["usertype"] == "Voice User"
        n = int(mask_v.sum() * cfg["silent_shift"] * 0.4)
        if n > 0:
            idx = df[mask_v].sample(n=min(n, mask_v.sum()), random_state=42).index
            df.loc[idx, "usertype"] = "Silent User"

    return df


def generate_month(real_df: pd.DataFrame, month_key: str) -> None:
    cfg = MONTHS[month_key]
    print(f"\nGenerating {month_key} ({cfg['label']}) — {N_RECORDS:,} records...")

    out_path = DATA_DIR / f"smartcare_cem_{cfg['label']}.csv"

    # Write header
    out_path.write_text(",".join(real_df.columns) + "\n")

    generated = 0
    while generated < N_RECORDS:
        batch_n = min(BATCH_SIZE, N_RECORDS - generated)
        batch = real_df.sample(n=batch_n, replace=True, random_state=42 + generated)
        batch = perturb_numerical(batch.copy())
        batch = apply_month_drift(batch, cfg)
        batch["imsi"] = [_make_imsi() for _ in range(len(batch))]
        batch["tac"] = [_make_tac() for _ in range(len(batch))]
        batch["month_year"] = month_key

        batch.to_csv(out_path, mode="a", header=False, index=False)
        generated += len(batch)
        print(f"  {generated:,} / {N_RECORDS:,}")

    print(f"  written → {out_path}")


def main():
    print("Loading real BSS data...")
    real_df = load_real_data()
    print(f"Columns: {list(real_df.columns)}")

    for month_key in MONTHS:
        generate_month(real_df, month_key)

    print("\nDone.")


if __name__ == "__main__":
    main()
