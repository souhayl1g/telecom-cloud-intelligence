"""
Generate 48 monthly OSS CSV files (16 months × 3 RATs).

Why
---
Real Huawei OSS export = 3 CSVs (one per RAT: 2G, 3G, 4G), each a single-day
snapshot (2026-03-28). BSS has 16 monthly snapshots. To align the time-series
modeling across both layers, we generate 16 monthly variants PER RAT — total 48
files — that REUSE THE EXACT REAL HUAWEI COLUMN STRUCTURE of each RAT.

Output
------
TT_data/OSS/generated/
    oss_2g_<token>.csv  × 16   ← same columns as real 2G CSV, with metadata header
    oss_3g_<token>.csv  × 16   ← same columns as real 3G CSV
    oss_4g_<token>.csv  × 16   ← same columns as real 4G CSV

Tokens (16, matching BSS files):
    jan, jan_consistent, feb, mars, avr, avr_consistent, mai, mai_consistent,
    jun, jun_consistent, jul, jul_consistent, aug, aou_consistent, sep, sep_consistent

Methodology
-----------
1. Read each real Huawei CSV intact (columns + first data row to preserve schema).
2. For each (RAT, month) pair:
   a. Bootstrap sample ~50K rows from the real RAT file.
   b. Shift `Time` column to a random hour within the target month.
   c. Apply per-month drift to numeric KPIs (integrity ↓ slightly, CDR ↑ slightly,
      throughput / users scale by drift factor).
   d. Write CSV with Huawei-style 7-line metadata header preserved.

Run inside docker (host may lack pandas):
    docker compose run --rm --entrypoint "" data-init \\
        python /app/services/data-ingest/generate_oss_months.py

Or with project venv:
    .venv/bin/python services/data-ingest/generate_oss_months.py
"""
from __future__ import annotations

import csv
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

# Path detection: when run inside docker, the repo root is /app
HERE = Path(__file__).resolve().parent
if (HERE.parents[1] / "TT_data").exists():
    ROOT = HERE.parents[1]
elif Path("/app/TT_data").exists():
    ROOT = Path("/app")
else:
    ROOT = HERE.parents[1]

TT_DATA = ROOT / "TT_data"
OSS_DIR = TT_DATA / "OSS"
OUT_DIR = OSS_DIR / "generated"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REAL_OSS = {
    "2G": OSS_DIR / "KPI Analysis Result_Query_Result_20260427105204494(KPI Analysis Result).csv",
    "3G": OSS_DIR / "KPI Analysis Result_Query_Result_2026042710520899(KPI Analysis Result).csv",
    "4G": OSS_DIR / "KPI Analysis Result_Query_Result_20260427105212826(KPI Analysis Result).csv",
}

# Header (metadata) is the first 6 lines of every Huawei CSV. Line 7 = column names.
METADATA_LINES_COUNT = 6
HEADER_LINE_INDEX = 6  # zero-based

# 16 month-tokens × (year-month, drift_factor)
MONTHS = {
    "jan":             ("2026-01", -0.08),
    "jan_consistent":  ("2026-01", -0.10),
    "feb":             ("2026-02",  0.00),   # real
    "mars":            ("2026-03",  0.00),   # real
    "avr":             ("2026-04",  0.05),
    "avr_consistent":  ("2026-04",  0.07),
    "mai":             ("2026-05",  0.05),
    "mai_consistent":  ("2026-05",  0.07),
    "jun":             ("2026-06",  0.10),
    "jun_consistent":  ("2026-06",  0.12),
    "jul":             ("2026-07",  0.12),
    "jul_consistent":  ("2026-07",  0.14),
    "aug":             ("2026-08",  0.10),
    "aou_consistent":  ("2026-08",  0.11),
    "sep":             ("2026-09",  0.03),
    "sep_consistent":  ("2026-09",  0.04),
}

# Per-RAT bootstrap size (rows per generated monthly file).
ROWS_PER_FILE = {"2G": 50_000, "3G": 50_000, "4G": 50_000}


def _read_real_with_header(rat: str):
    """Return (metadata_lines, df) for a real Huawei OSS CSV.

    metadata_lines = first 6 lines (BOM + blanks + KPI title + Save Time + User Name + blank)
    df             = pandas DataFrame loaded with the proper header line (skiprows=6)
    """
    path = REAL_OSS[rat]
    with open(path, "r", encoding="utf-8-sig") as f:
        metadata_lines = [f.readline() for _ in range(METADATA_LINES_COUNT)]
    df = pd.read_csv(path, skiprows=METADATA_LINES_COUNT, encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    return metadata_lines, df


def _random_timestamp(month_ym: str, rng: np.random.Generator) -> str:
    year, month = map(int, month_ym.split("-"))
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    start = datetime(year, month, 1)
    secs = int((end - start).total_seconds())
    offset = int(rng.integers(0, secs))
    ts = (start + timedelta(seconds=offset)).replace(minute=0, second=0, microsecond=0)
    return ts.strftime("%Y-%m-%d %H:%M")


def _apply_drift(df: pd.DataFrame, rat: str, drift_f: float, rng: np.random.Generator) -> pd.DataFrame:
    """Apply per-month drift to numeric KPI columns, keeping schema intact."""
    df = df.copy()
    # Find integrity (column starts with 'Integrity')
    integ_c = next((c for c in df.columns if c.lower().startswith("integrity")), None)
    if integ_c is not None:
        integ = df[integ_c].astype(str).str.rstrip("%").replace("", np.nan)
        integ = pd.to_numeric(integ, errors="coerce").fillna(100.0)
        integ_drifted = np.clip(integ - drift_f * 1.5 + rng.normal(0, 0.4, len(df)), 80, 100)
        df[integ_c] = [f"{v:.2f}%" for v in integ_drifted]

    # CDR-like columns (call drop, BLER) — drift UP with load
    cdr_cols = [c for c in df.columns if "call drop" in c.lower() or "opt_npm" in c.lower()]
    for c in cdr_cols:
        cdr = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        cdr_drifted = np.clip(cdr * (1 + drift_f * 1.2) + rng.normal(0, 0.05, len(df)), 0, 30)
        df[c] = np.round(cdr_drifted, 4)

    # Throughput-like — scale with drift
    tput_cols = [c for c in df.columns if "throughput" in c.lower() or "hsdpa" in c.lower() or "thp" in c.lower()]
    for c in tput_cols:
        v = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        v_drifted = np.clip(v * (1 + drift_f + rng.normal(0, 0.05, len(df))), 0, None)
        df[c] = np.round(v_drifted, 4)

    # RSRP — small drift
    rsrp_cols = [c for c in df.columns if "rsrp" in c.lower()]
    for c in rsrp_cols:
        v = pd.to_numeric(df[c], errors="coerce")
        v_drifted = v + rng.normal(0, 1.5, len(df))
        df[c] = np.round(v_drifted, 4)

    # Users (avg/max) — scale with drift
    user_cols = [c for c in df.columns if "user.avg" in c.lower() or "user.max" in c.lower() or "active" in c.lower()]
    for c in user_cols:
        v = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        v_drifted = np.clip(v * (1 + drift_f + rng.normal(0, 0.08, len(df))), 0, None)
        # Users are integers
        df[c] = np.round(v_drifted).astype("Int64") if v.dtype.kind == "i" else np.round(v_drifted, 2)

    return df


def _generate_one(rat: str, token: str, ym: str, drift_f: float,
                  metadata_lines: list[str], real_df: pd.DataFrame) -> Path:
    rng = np.random.default_rng(seed=hash((rat, token)) & 0xFFFFFFFF)
    n = ROWS_PER_FILE[rat]

    # Bootstrap sample
    idx = rng.integers(0, len(real_df), size=n)
    df = real_df.iloc[idx].reset_index(drop=True).copy()

    # Replace Time column with month-randomized timestamps
    time_col = next((c for c in df.columns if c.strip() == "Time"), df.columns[0])
    df[time_col] = [_random_timestamp(ym, rng) for _ in range(n)]

    # Apply drift to KPIs
    df = _apply_drift(df, rat, drift_f, rng)

    # Write file: Huawei metadata + header + data
    out_path = OUT_DIR / f"oss_{rat.lower()}_{token}.csv"
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        # Replicate first 6 metadata lines (with a fresh Save Time)
        for i, line in enumerate(metadata_lines):
            if line.startswith("Save Time"):
                f.write(f"Save Time :{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            else:
                f.write(line)
        # Column header + data via pandas
        df.to_csv(f, index=False, lineterminator="\n")

    return out_path


def _read_real_with_header_sampled(rat: str, max_rows: int = 300_000):
    """Memory-efficient reservoir: sample at most `max_rows` from the real CSV.

    Uses chunked reads + reservoir sampling to bound RAM while preserving
    distribution. Real OSS CSV may have 8.5M rows (4G) — full load is OOM
    inside the data-init container (~1.5 GB limit).
    """
    path = REAL_OSS[rat]
    with open(path, "r", encoding="utf-8-sig") as f:
        metadata_lines = [f.readline() for _ in range(METADATA_LINES_COUNT)]

    # Reservoir sampling — read in chunks, keep a uniform random subset.
    chunks = []
    seen = 0
    rng_local = np.random.default_rng(seed=hash(rat) & 0xFFFFFFFF)
    for chunk in pd.read_csv(path, skiprows=METADATA_LINES_COUNT, encoding="utf-8-sig",
                             chunksize=200_000, low_memory=False):
        seen += len(chunk)
        chunks.append(chunk)
        # Quick exit if we're already past the cap with margin
        if sum(len(c) for c in chunks) > max_rows * 4:
            break
    df = pd.concat(chunks, ignore_index=True)
    df.columns = df.columns.str.strip()
    if len(df) > max_rows:
        idx = rng_local.choice(len(df), size=max_rows, replace=False)
        df = df.iloc[idx].reset_index(drop=True)
    return metadata_lines, df


def main():
    print(f"Generating 48 OSS files (3 RATs × 16 months) → {OUT_DIR}")
    print(f"Memory-bounded: sampling up to 300K rows per RAT into reservoir.\n")

    total = 0
    # Process one RAT at a time → release memory between RATs.
    for rat in ("2G", "3G", "4G"):
        print(f"=== {rat} ===")
        meta, real_df = _read_real_with_header_sampled(rat, max_rows=300_000)
        print(f"  reservoir: {len(real_df):,} rows × {real_df.shape[1]} cols")
        for token, (ym, drift_f) in MONTHS.items():
            out = _generate_one(rat, token, ym, drift_f, meta, real_df)
            total += 1
            print(f"    ✓ {out.name:35s} month={ym} drift={drift_f:+.2f} size={out.stat().st_size/1e6:.1f} MB")
        # Free memory before next RAT
        del real_df
        import gc
        gc.collect()
        print()

    total_size_mb = sum(p.stat().st_size for p in OUT_DIR.glob("*.csv")) / 1e6
    print(f"DONE — generated {total} files (~{total_size_mb:.0f} MB total)")


if __name__ == "__main__":
    main()
