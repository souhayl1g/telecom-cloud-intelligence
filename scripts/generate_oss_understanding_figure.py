#!/usr/bin/env python3
"""Data Understanding hero figure — real OSS KPI distributions.

Six panels: 4 raw vendor KPIs + 2 ETL-engineered KPIs, values pulled live
from oss_cell_kpis (18.8M real rows), no fault-injection split. Answers
"what does the network data actually look like" for the jury, not a
model-validation question.

Raw vs engineered split is not a guess — it is read straight off
services/data-ingest/ingest_oss_real.py:50-51,176-178, where latency_ms and
packet_loss_rate are explicitly commented "not in source, derived by
vw_oss_cell_derived". throughput_mbps, rsrp_dbm, active_users, cell_load_pct
are vendor columns present in the 2G/3G/4G source export.

Usage:
    python3 scripts/generate_oss_understanding_figure.py
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "report" / "figures" / "eda" / "oss_real_distributions.png"

TEAL = "#00B4D8"
ORANGE = "#FF6B35"
INK = "#0D1117"
GRID = "#D8DEE6"
MUTED = "#5A6472"

# view_col -> (display label, unit, kind)  kind: "raw" | "eng"
# throughput_mbps/rsrp_dbm/active_users are vendor columns carried straight
# through the view. cell_load_pct_real/latency_ms_derived/packet_loss_pct_derived
# only exist in vw_oss_cell_derived — the base oss_cell_kpis columns of the
# same un-suffixed name are all-NULL placeholders (confirmed via COUNT(col)=0).
KPIS = [
    ("throughput_mbps", "Throughput", "Mbps", "raw"),
    ("rsrp_dbm", "Signal RSRP", "dBm", "raw"),
    ("active_users", "Active Users", "count", "raw"),
    ("cell_load_pct_real", "Cell Load", "%", "raw"),
    ("latency_ms_derived", "Latency", "ms", "eng"),
    ("packet_loss_pct_derived", "Packet Loss", "%", "eng"),
]

SAMPLE_PCT = 2  # TABLESAMPLE SYSTEM percent — same convention as routers/explorer.py


def psql(sql: str) -> str:
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres",
         "psql", "-U", "telecom", "-d", "telecom_intel", "-tAc", sql],
        cwd=REPO, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"psql failed:\n{proc.stderr.strip()}")
    return proc.stdout.strip()


def fetch_values(col: str) -> np.ndarray:
    # vw_oss_cell_derived is a plain (non-materialized) view — TABLESAMPLE
    # can't target it directly, so sample the base table's id column and
    # join back into the view (1:1 row correspondence, cheap PK lookup).
    out = psql(
        f"SELECT v.{col} FROM vw_oss_cell_derived v "
        f"JOIN (SELECT id FROM oss_cell_kpis TABLESAMPLE SYSTEM ({SAMPLE_PCT})) s "
        f"ON v.id = s.id "
        f"WHERE v.{col} IS NOT NULL;"
    )
    if not out:
        return np.array([])
    return np.array([float(x) for x in out.splitlines()], dtype="float64")


def total_rows() -> int:
    return int(psql("SELECT COUNT(*) FROM oss_cell_kpis;"))


def skew(x: np.ndarray) -> float:
    m, s = x.mean(), x.std()
    return float(((x - m) ** 3).mean() / (s**3)) if s else 0.0


def make_figure():
    n_total = total_rows()
    print(f"querying live postgres · oss_cell_kpis · {n_total:,} real rows total")

    fig, axes = plt.subplots(2, 3, figsize=(13, 7.4))
    fig.patch.set_facecolor("white")

    for ax, (col, label, unit, kind) in zip(axes.flat, KPIS):
        vals = fetch_values(col)
        p1, p99 = np.percentile(vals, [1, 99])
        disp = np.clip(vals, p1, p99)
        color = TEAL if kind == "raw" else ORANGE
        tag = "RAW" if kind == "raw" else "ENGINEERED"

        ax.hist(disp, bins=50, color=color, alpha=0.85, edgecolor="white", linewidth=0.3)
        ax.set_title(f"{label}  ({unit})", fontsize=12, fontweight="bold",
                     color=INK, loc="left")
        ax.text(0.97, 0.93, tag, transform=ax.transAxes, ha="right", va="top",
                fontsize=8.5, fontweight="bold", color=color)
        ax.text(0.97, 0.83, f"mean={vals.mean():.1f}  skew={skew(vals):+.1f}",
                transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=MUTED)
        ax.text(0.97, 0.75, f"n={len(vals):,}", transform=ax.transAxes,
                ha="right", va="top", fontsize=8, color=MUTED)

        ax.set_ylabel("density", fontsize=8.5, color="#555")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color=GRID, linewidth=0.6, alpha=0.7)
        ax.tick_params(labelsize=8, colors="#555")

        print(f"  {col:20s} kind={kind:4s} n={len(vals):>7,} "
              f"mean={vals.mean():.2f} skew={skew(vals):+.2f}")

    fig.suptitle(
        f"OSS Network KPI Distributions — {n_total:,} real cell-level records "
        f"(TABLESAMPLE {SAMPLE_PCT}% for plotting)",
        fontsize=11.5, color=INK, fontweight="bold", y=1.01)
    fig.text(0.5, -0.01,
              "TEAL = raw vendor column (2G/3G/4G export)  ·  "
              "ORANGE = ETL-engineered (not in vendor source, computed by vw_oss_cell_derived)",
              ha="center", fontsize=8.5, color=MUTED, style="italic")

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160, bbox_inches="tight", facecolor="white")
    print(f"saved {OUT}")


if __name__ == "__main__":
    make_figure()
