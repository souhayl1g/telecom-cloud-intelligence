#!/usr/bin/env python3
"""Data Preparation hero figure — three real steps notebook 01 applies.

Three panels, all computed live from the real TT_data/BSS source files
(Feb + Mar 2026, the only real months — Jan/Apr/May are bootstrap-simulated
and excluded here):

  A. Missingness — % NaN per raw BSS column. Traffic/duration/rate columns
     come back 0% missing; the real gaps are in device/technical fields
     (sim_slot, volte_flag, tac, model/brand/tertype/generation, area) —
     handled by categorical fillna('Unknown') or IterativeImputer depending
     on dtype (notebook 01 §7-8).

  B. Winsorize p99 — raw vs capped distribution for traffic_4g, the same
     column and the same 0.99 quantile the real pipeline clips at
     (notebook 01 §8: `p99 = df[c].quantile(0.99); df[c].clip(upper=p99)`).

  C. Derived feature — traffic_4g_share = traffic_4g / dou_total, the same
     ratio notebook 01 §14-17 computes and feeds into the CEM target formula
     (0.30 weight). Raw columns alone don't expose this ratio; the model
     would have to learn division to approximate it, so feature engineering
     hands it over directly. NOT log1p — that transform only ever appears
     in notebook 00 as an EDA display choice (log-axis for |skew|>1 plots),
     never as a feature baked into the training data. Tree ensembles
     (LightGBM/XGBoost) split on rank order, so a monotonic transform like
     log1p wouldn't change what they learn anyway; the one real scaling
     step in the whole pipeline is VAE's StandardScaler (notebook 03),
     which is model-specific and out of scope for this ETL-stage figure.

Both numbers are recomputed here, not copied from the notebook's printed
log — if the pipeline or the source files change, this figure changes too.

TT_data/ is confidential and gitignored; this script reads it locally only,
the PNG it writes contains no raw records, only aggregate statistics.

Usage:
    python3 scripts/generate_data_prep_pipeline_figure.py
"""

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "report" / "figures" / "dataprep_pipeline_real.png"

# Real months only — Jan/Apr/May in TT_data/BSS/ are bootstrap-simulated fill-in.
REAL_FILES = [
    REPO / "TT_data" / "BSS" / "smartcare_cem_feb.csv",
    REPO / "TT_data" / "BSS" / "smartcare_cem_mars.csv",
]

TEAL = "#00B4D8"
ORANGE = "#FF6B35"
INK = "#0D1117"
GRID = "#D8DEE6"
MUTED = "#5A6472"

# Real missingness in this dataset lives in device/technical columns, not the
# traffic/rate numerics — confirmed by a full-column NaN scan (sim_slot ~76%,
# volte_flag ~75% on Feb alone). Report ALL raw columns, not a curated subset,
# so the figure isn't cherry-picking a flattering story.
WINSOR_COL = "traffic_4g"

# Derived feature (notebook 01 §14-17): the ratio a model can't discover
# from raw traffic_4g + dou_total alone, and the same column that feeds
# the CEM target formula's 0.30 weight.
SHARE_NUM_COL = "traffic_4g"
SHARE_DEN_COL = "dou_total"


def load_real_bss() -> pd.DataFrame:
    frames = [pd.read_csv(f, low_memory=False) for f in REAL_FILES]
    return pd.concat(frames, ignore_index=True)


def compute_missingness(df: pd.DataFrame) -> pd.Series:
    pct_nan = df.isna().mean() * 100
    pct_nan = pct_nan[pct_nan > 0].sort_values(ascending=False)
    return pct_nan


def make_figure():
    print("reading real TT_data/BSS CSVs (Feb + Mar 2026, local only) ...")
    df = load_real_bss()
    n = len(df)
    print(f"  loaded {n:,} real subscriber-month rows")

    pct_nan = compute_missingness(df)
    print("  missingness per column:")
    for col, pct in pct_nan.items():
        print(f"    {col:20s} {pct:5.2f}% NaN")

    raw = pd.to_numeric(df[WINSOR_COL], errors="coerce").dropna()
    raw = raw[raw >= 0]
    p99 = raw.quantile(0.99)
    n_capped = int((raw > p99).sum())
    winsorized = raw.clip(upper=p99)
    print(f"  winsorize {WINSOR_COL}: p99={p99:.2f}  capped {n_capped:,} of {len(raw):,} rows")

    dou = pd.to_numeric(df[SHARE_DEN_COL], errors="coerce")
    t4g = pd.to_numeric(df[SHARE_NUM_COL], errors="coerce")
    share = (t4g / dou.replace(0, np.nan)).clip(0, 1).dropna()
    print(f"  derived traffic_4g_share: n={len(share):,}  mean={share.mean():.3f}  "
          f"median={share.median():.3f}")

    fig, (axA, axB, axC) = plt.subplots(1, 3, figsize=(18, 5))
    fig.patch.set_facecolor("white")

    # Panel A — missingness (real gaps: device/technical columns, not usage)
    cols = list(pct_nan.index)
    vals = pct_nan.values
    axA.barh(cols, vals, color=ORANGE, alpha=0.85, edgecolor="white", height=0.65)
    axA.invert_yaxis()
    axA.set_xlabel("% missing (before IterativeImputer / categorical fill)",
                    fontsize=9.5, color="#444")
    axA.set_title("A · Missingness — real BSS columns", fontsize=12.5,
                   fontweight="bold", color=INK, loc="left")
    for i, v in enumerate(vals):
        axA.text(v + 0.8, i, f"{v:.1f}%", va="center", fontsize=8.3, color=MUTED)
    axA.spines[["top", "right"]].set_visible(False)
    axA.tick_params(labelsize=8.5, colors="#444")
    axA.set_xlim(0, vals.max() * 1.18)
    axA.text(0.98, -0.14, "traffic/usage/rate columns: 0% missing (not shown)",
              transform=axA.transAxes, ha="right", fontsize=7.8, color=MUTED,
              style="italic")

    # Panel B — winsorize p99, in GB (raw column is byte-scale) and zoomed to
    # the p99 cutoff itself so the cap is actually visible, not buried 10x out.
    raw_gb = raw / 1e9
    winsorized_gb = winsorized / 1e9
    p99_gb = p99 / 1e9
    disp_max = p99_gb * 1.15
    raw_disp = np.clip(raw_gb, 0, disp_max)

    axB.hist(raw_disp, bins=60, range=(0, disp_max), color="#C7CFDA", alpha=0.9,
              edgecolor="white", linewidth=0.3, label="raw")
    axB.hist(winsorized_gb, bins=60, range=(0, disp_max), color=TEAL, alpha=0.75,
             edgecolor="white", linewidth=0.3, label="winsorized (p99 cap)")
    axB.axvline(p99_gb, color=ORANGE, linewidth=1.8, linestyle="--")
    axB.text(p99_gb, axB.get_ylim()[1] * 0.92, f"  p99 = {p99_gb:.1f} GB",
              color=ORANGE, fontsize=9, fontweight="bold")
    axB.set_xlim(0, disp_max)
    axB.set_title(f"B · Winsorize p99 — {WINSOR_COL}", fontsize=12.5,
                   fontweight="bold", color=INK, loc="left")
    axB.set_xlabel(f"{WINSOR_COL}  (GB, display zoomed to p99 cutoff)",
                    fontsize=9, color="#444")
    axB.set_ylabel("subscribers", fontsize=9, color="#444")
    axB.legend(fontsize=8.5, frameon=False)
    axB.spines[["top", "right"]].set_visible(False)
    axB.grid(axis="y", color=GRID, linewidth=0.6, alpha=0.7)
    axB.tick_params(labelsize=8.5, colors="#444")
    axB.text(0.97, 0.72, f"capped {n_capped:,} of\n{len(raw):,} rows\n"
              f"({n_capped/len(raw)*100:.1f}%, expected ~1%)",
              transform=axB.transAxes, ha="right", va="top", fontsize=8.3, color=MUTED)

    # Panel C — derived feature engineering: traffic_4g_share, the ratio
    # notebook 01 computes and feeds into the CEM target's 0.30 weight term.
    # Real transform step (unlike log1p, which is EDA-only — see docstring).
    axC.hist(share, bins=60, range=(0, 1), color=TEAL, alpha=0.85,
              edgecolor="white", linewidth=0.3)
    axC.axvline(share.median(), color=ORANGE, linewidth=1.8, linestyle="--")
    axC.text(share.median(), axC.get_ylim()[1] * 0.92,
              f"  median = {share.median():.2f}", color=ORANGE, fontsize=9,
              fontweight="bold")
    axC.set_xlim(0, 1)
    axC.set_title("C · Derived Feature — traffic_4g_share", fontsize=12.5,
                   fontweight="bold", color=INK, loc="left")
    axC.set_xlabel("traffic_4g / dou_total  (ratio, feeds CEM formula 0.30 weight)",
                    fontsize=9, color="#444")
    axC.set_ylabel("subscribers", fontsize=9, color="#444")
    axC.spines[["top", "right"]].set_visible(False)
    axC.grid(axis="y", color=GRID, linewidth=0.6, alpha=0.7)
    axC.tick_params(labelsize=8.5, colors="#444")
    axC.text(0.02, 0.95, "not log1p — raw ratio the model\ncan't discover on its own",
              transform=axC.transAxes, ha="left", va="top", fontsize=7.8, color=MUTED,
              style="italic")

    fig.suptitle(
        f"Data Preparation — real steps from notebooks/01_etl_feature_engineering.ipynb "
        f"({n:,} real subscriber-month rows, Feb+Mar 2026)",
        fontsize=11.5, color=INK, fontweight="bold", y=1.02)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160, bbox_inches="tight", facecolor="white")
    print(f"saved {OUT}")


if __name__ == "__main__":
    make_figure()
