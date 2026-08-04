"""
Phase 3 - Data Preparation hero figure(s).
ONE real feature, before -> after log1p, per figure. Integrity-first:
values read straight from real project data, never invented.

Usage:
    python3 scripts/generate_dataprep_figure.py dou_total
    python3 scripts/generate_dataprep_figure.py traffic_4g
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

# Brand palette (defense theme)
TEAL = "#00B4D8"
ORANGE = "#FF6B35"
INK = "#0D1117"
GRID = "#D8DEE6"

# Each feature declares where its REAL values come from.
# npz  -> v3 training matrix (already feature-engineered, model-fed values)
# csv  -> raw BSS source file (TT_data/, confidential, stays local, never committed)
FEATURE_SOURCES = {
    "dou_total": {
        "kind": "npz",
        "path": "notebooks/data/cem_combined_v3.npz",
    },
    "traffic_4g": {
        "kind": "csv",
        "path": "TT_data/BSS/smartcare_cem_feb.csv",  # confidential, gitignored, local only
    },
}


def skew(x):
    m = x.mean()
    s = x.std()
    return float(((x - m) ** 3).mean() / (s**3)) if s else 0.0


def load_raw_values(feature):
    src = FEATURE_SOURCES[feature]
    if src["kind"] == "npz":
        # allow_pickle: NPZ generated locally by our own training pipeline
        # (notebooks/02_cem_score_training.ipynb), never external input.
        d = np.load(src["path"], allow_pickle=True)
        names = [str(x) for x in d["feature_names"]]
        col = names.index(feature)
        raw = d["X_train"][:, col].astype("float64")
    else:
        df = pd.read_csv(src["path"], usecols=[feature])
        raw = df[feature].dropna().values.astype("float64")
    raw = raw[np.isfinite(raw) & (raw >= 0)]
    return raw, src["path"]


def make_figure(feature):
    raw, source_path = load_raw_values(feature)

    # winsorise display at p99 so the long tail doesn't crush the raw panel
    p99 = np.percentile(raw, 99)
    raw_disp = np.clip(raw, 0, p99)
    logged = np.log1p(raw)

    sk_raw, sk_log = skew(raw), skew(logged)
    n = len(raw)
    out = f"report/figures/dataprep_log1p_{feature}.png"

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.2))
    fig.patch.set_facecolor("white")

    axL.hist(raw_disp, bins=60, color=ORANGE, alpha=0.85, edgecolor="white", linewidth=0.3)
    axL.set_title(f"RAW  ·  {feature}", fontsize=13, fontweight="bold", color=INK, loc="left")
    axL.text(0.97, 0.92, f"skew = +{sk_raw:.1f}", transform=axL.transAxes,
              ha="right", fontsize=12, fontweight="bold", color=ORANGE)
    axL.text(0.97, 0.82, "spike at zero · long right tail", transform=axL.transAxes,
              ha="right", fontsize=9, color="#666")

    axR.hist(logged, bins=60, color=TEAL, alpha=0.85, edgecolor="white", linewidth=0.3)
    axR.set_title(f"AFTER log1p  ·  {feature}", fontsize=13, fontweight="bold", color=INK, loc="left")
    axR.text(0.97, 0.92, f"skew = {sk_log:+.1f}", transform=axR.transAxes,
              ha="right", fontsize=12, fontweight="bold", color=TEAL)
    axR.text(0.97, 0.82, "spread out · tree-friendly", transform=axR.transAxes,
              ha="right", fontsize=9, color="#666")

    for ax in (axL, axR):
        ax.set_ylabel("subscribers", fontsize=9, color="#555")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color=GRID, linewidth=0.6, alpha=0.7)
        ax.tick_params(labelsize=8, colors="#555")

    arrow = FancyArrowPatch((0.485, 0.5), (0.515, 0.5), transform=fig.transFigure,
                             arrowstyle="-|>", mutation_scale=22, lw=2.4, color=INK)
    fig.add_artist(arrow)
    fig.text(0.5, 0.57, "log1p", ha="center", fontsize=11, fontweight="bold", color=INK)

    fig.suptitle(f"One transform, measured on {n:,} real subscriber records",
                 fontsize=11, color="#444", y=0.02)
    fig.tight_layout(rect=[0, 0.04, 1, 0.98])
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    print(f"saved {out}  |  source={source_path}  |  raw skew +{sk_raw:.2f} -> "
          f"log1p skew {sk_log:+.2f}  |  n={n:,}")


if __name__ == "__main__":
    feature = sys.argv[1] if len(sys.argv) > 1 else "dou_total"
    if feature not in FEATURE_SOURCES:
        sys.exit(f"unknown feature '{feature}', options: {list(FEATURE_SOURCES)}")
    make_figure(feature)
