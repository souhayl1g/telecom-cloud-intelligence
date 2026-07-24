#!/usr/bin/env python3
"""Render the BSS and OSS feature-provenance figures for the defense deck.

Both figures answer the same question from opposite sides: which columns exist
in the source data, which ones we engineered, and which ones only exist because
OSS and BSS were joined on geography.

Integrity rules this script follows:

  * Feature names are read from the *_feature_names.joblib artefacts, which are
    the same files services/ai-service loads at startup. The figure therefore
    cannot claim a feature the deployed models do not consume.
  * RAW vs DERIVED is decided by asking the live database which columns really
    exist, not by a hardcoded list. A retrain that widens the feature set
    re-buckets the figure automatically.
  * Row and subscriber counts come from live queries at render time.
  * Nothing is drawn that could not be traced back to an artefact or a query.

Usage:
    python3 scripts/generate_feature_figures.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MODELS = REPO / "notebooks" / "models"
OUT_DIR = REPO / "report" / "figures"

INK = "#0D1117"
MUTED = "#5A6472"
BLUE = "#1668B3"
ORANGE = "#E8590C"
TEAL = "#0E9F6E"
PAGE = "#FFFFFF"

# Real BSS months. The simulated months are excluded so the caption reports
# genuine Tunisie Telecom volume only.
BSS_REAL_MONTHS = ("2026-02", "2026-03")

# The three OSS KPIs that are not in the vendor export - the ETL computes them.
# Kept explicit because a derived column has no database row to detect it by.
OSS_DERIVED = ("latency_ms_derived", "packet_loss_pct_derived", "jitter_ms_derived")

# Columns that carry no signal for a feature figure (keys, bookkeeping).
#
# latency_ms / packet_loss_rate / jitter_ms are deliberately excluded from the
# raw band: the columns exist in PostgreSQL, but the vendor 2G/3G/4G exports
# never carried them - the ETL computes them, which is why the VAE contract
# names them *_derived. Listing them as raw would contradict the derived band.
OSS_SKIP = {"id", "created_at", "timestamp", "anomaly_flag", "source",
            "site_name", "active_users_max",
            "latency_ms", "packet_loss_rate", "jitter_ms"}


# --------------------------------------------------------------------------
# Live facts
# --------------------------------------------------------------------------


def psql(sql: str) -> str:
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres",
         "psql", "-U", "telecom", "-d", "telecom_intel", "-tAc", sql],
        cwd=REPO, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"psql failed:\n{proc.stderr.strip()}")
    return proc.stdout.strip()


def columns_of(table: str) -> set[str]:
    out = psql(
        "SELECT string_agg(column_name,',') FROM information_schema.columns "
        f"WHERE table_name='{table}';"
    )
    return set(out.split(",")) if out else set()


def gather_facts() -> dict:
    months = "','".join(BSS_REAL_MONTHS)
    return {
        "bss_cols": columns_of("bss_subscribers"),
        "oss_cols": columns_of("oss_cell_kpis"),
        # Distinct IMSI, not row count: the same subscriber appears in both real
        # months, so rows would double-count people.
        "bss_subscribers": int(psql(
            f"SELECT COUNT(DISTINCT imsi_hash) FROM bss_subscribers "
            f"WHERE month_year IN ('{months}');")),
        "bss_rows": int(psql(
            f"SELECT COUNT(*) FROM bss_subscribers "
            f"WHERE month_year IN ('{months}');")),
        "oss_rows": int(psql("SELECT COUNT(*) FROM oss_cell_kpis;")),
        "oss_cells": int(psql("SELECT COUNT(DISTINCT cell_id) FROM oss_cell_kpis;")),
    }


def bucket_bss(facts: dict) -> tuple[list[str], list[str], list[str]]:
    """Split the CEM feature contract into raw / derived / area-joined."""
    # joblib.load is pickle-backed, so it only stays safe on trusted files.
    # This path is a first-party artefact written by notebooks/02 and already
    # loaded by services/ai-service at startup - no external input reaches it.
    feats = list(joblib.load(MODELS / "cem_v3_feature_names.joblib"))
    raw = [f for f in feats if f in facts["bss_cols"]]
    area = [f for f in feats if f.endswith("_area")]
    derived = [f for f in feats if f not in raw and f not in area]
    return raw, derived, area


def bucket_oss(facts: dict) -> tuple[list[str], list[str], list[str]]:
    """Raw vendor KPI columns, the three derived KPIs, and the area roll-up."""
    raw = sorted(facts["oss_cols"] - OSS_SKIP)
    # Lead with the KPIs a reader recognises, then the keys.
    lead = ["integrity", "throughput_mbps", "rsrp_dbm", "call_drop_rate",
            "active_users", "cell_load_pct", "latency_ms", "packet_loss_rate",
            "jitter_ms"]
    raw = [c for c in lead if c in raw] + [c for c in raw if c not in lead]
    derived = list(OSS_DERIVED)
    _, _, area = bucket_bss(facts)
    return raw, derived, area


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------

# Layout runs in an isotropic data coordinate system: x spans 0..100 units and
# the figure height is derived from the content, so one unit is the same
# physical distance on both axes. Axes-fraction units would not work here -
# they stretch with the figure aspect while font sizes stay in absolute points,
# so chips would grow out of proportion to the text inside them.
FIG_W_IN = 9.4
UNITS_W = 100.0
PT_PER_UNIT = FIG_W_IN * 72 / UNITS_W  # ~6.77 pt per unit

CHIP_FS = 8.3          # monospace point size inside a chip
CHIP_H = 3.6
CHIP_GAP = 1.1
ROW_GAP = 1.5
PAD_X = 3.2
# DejaVu Sans Mono advances ~0.602 em; convert points to layout units.
CHAR_W = CHIP_FS * 0.602 / PT_PER_UNIT


def chip_width(label: str) -> float:
    return len(label) * CHAR_W + 2.6


def layout_rows(labels: list[str], max_w: float) -> list[list[str]]:
    """Greedy flow layout - wrap chips into rows that fit the container."""
    rows: list[list[str]] = [[]]
    w = 0.0
    for lab in labels:
        cw = chip_width(lab)
        if rows[-1] and w + CHIP_GAP + cw > max_w:
            rows.append([])
            w = 0.0
        rows[-1].append(lab)
        w += cw + (CHIP_GAP if len(rows[-1]) > 1 else 0)
    return rows


HEADER_H = 6.4      # space above the first chip row for the numbered heading
FOOTER_H = 5.6      # divider + subcaption below the last chip row
BAND_GAP = 5.2      # arrow gutter between bands
TITLE_H = 8.0
NOTE_H = 5.0


def band_height(labels: list[str], max_w: float) -> float:
    n = len(layout_rows(labels, max_w))
    return HEADER_H + n * CHIP_H + (n - 1) * ROW_GAP + FOOTER_H


def draw_band(ax, y_top: float, labels: list[str], number: str, heading: str,
              meta: str, subcaption: str, color: str) -> float:
    """Draw one numbered section; returns the y of its bottom edge."""
    inner_w = UNITS_W - 2 * PAD_X
    rows = layout_rows(labels, inner_w)
    h = band_height(labels, inner_w)
    y_bot = y_top - h

    ax.add_patch(FancyBboxPatch(
        (0.9, y_bot), UNITS_W - 1.8, h,
        boxstyle="round,pad=0,rounding_size=1.1",
        facecolor="white", edgecolor=color, linewidth=1.6, zorder=1))

    hy = y_top - 3.3
    ax.plot([PAD_X + 1.0], [hy], marker="o", markersize=14, color=color, zorder=3)
    ax.text(PAD_X + 1.0, hy, number, ha="center", va="center", fontsize=9.5,
            fontweight="bold", color="white", zorder=4)
    head = ax.text(PAD_X + 3.4, hy, heading, ha="left", va="center",
                   fontsize=13.0, fontweight="bold", color=color, zorder=4)
    # Measure the rendered heading instead of estimating from character count -
    # a per-character guess under-runs on long headings and the meta text then
    # overlaps it (proportional fonts vary far too much per glyph).
    ax.figure.canvas.draw()
    bbox = head.get_window_extent(renderer=ax.figure.canvas.get_renderer())
    head_end = ax.transData.inverted().transform(bbox.corners()[3])[0]
    ax.text(head_end + 1.6, hy, meta, ha="left", va="center",
            fontsize=8.6, color=MUTED, zorder=4)

    y = y_top - HEADER_H - CHIP_H
    for row in rows:
        x = PAD_X
        for lab in row:
            cw = chip_width(lab)
            ax.add_patch(FancyBboxPatch(
                (x, y), cw, CHIP_H,
                boxstyle="round,pad=0,rounding_size=0.85",
                facecolor="white", edgecolor=color, linewidth=1.15, zorder=3))
            ax.text(x + cw / 2, y + CHIP_H / 2, lab, ha="center", va="center",
                    fontsize=CHIP_FS, color=INK, family="monospace", zorder=4)
            x += cw + CHIP_GAP
        y -= CHIP_H + ROW_GAP

    div_y = y_bot + FOOTER_H - 1.4
    ax.plot([PAD_X, UNITS_W - PAD_X], [div_y, div_y], linestyle=(0, (2, 3)),
            linewidth=0.9, color="#C7CFDA", zorder=2)
    ax.text(UNITS_W / 2, y_bot + 1.9, subcaption, ha="center", va="center",
            fontsize=8.9, color=MUTED, zorder=4)
    return y_bot


def render(path: Path, title: str, bands: list[dict], footnote: str) -> None:
    inner_w = UNITS_W - 2 * PAD_X
    content = sum(band_height(b["labels"], inner_w) for b in bands)
    total_h = TITLE_H + content + BAND_GAP * (len(bands) - 1) + NOTE_H

    # Square units: the figure is exactly as tall as the content demands.
    fig = plt.figure(figsize=(FIG_W_IN, FIG_W_IN * total_h / UNITS_W),
                     dpi=300, facecolor=PAGE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, UNITS_W)
    ax.set_ylim(0, total_h)

    y = total_h
    ax.text(UNITS_W / 2, y - 3.4, title, ha="center", va="center",
            fontsize=20.0, fontweight="bold", color=INK)
    y -= TITLE_H

    for i, b in enumerate(bands):
        y = draw_band(ax, y, b["labels"], str(i + 1), b["heading"],
                      b["meta"], b["subcaption"], b["color"])
        if i < len(bands) - 1:
            ax.add_patch(FancyArrowPatch(
                (UNITS_W / 2, y - 0.9), (UNITS_W / 2, y - BAND_GAP + 0.9),
                arrowstyle="-|>", mutation_scale=14, linewidth=1.7,
                color="#9AA5B4", zorder=3))
            y -= BAND_GAP

    ax.text(UNITS_W / 2, y - NOTE_H / 2, footnote, ha="center", va="center",
            fontsize=7.4, color=MUTED, style="italic", zorder=4)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, facecolor=PAGE)
    plt.close(fig)
    print(f"wrote {path}")


# --------------------------------------------------------------------------


def main() -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"
    print("querying live postgres ...")
    facts = gather_facts()

    raw, derived, area = bucket_bss(facts)
    print(f"  CEM contract : {len(raw)} raw + {len(derived)} derived "
          f"+ {len(area)} area = {len(raw) + len(derived) + len(area)}")
    print(f"  BSS real     : {facts['bss_subscribers']:,} distinct subscribers "
          f"over {facts['bss_rows']:,} subscriber-month rows")

    render(
        OUT_DIR / "bss_features.png",
        "BSS Subscriber Features",
        [
            dict(labels=raw, heading="RAW BSS", color=BLUE,
                 meta=f"  ·  {len(raw)} columns  ·  "
                      f"{facts['bss_subscribers']:,} real Tunisie Telecom subscribers",
                 subcaption="device capability · data volume · per-RAT traffic · "
                            "voice time · attach success rates"),
            dict(labels=derived, heading="DERIVED", color=ORANGE,
                 meta=f"  ·  {len(derived)} engineered features",
                 subcaption="ratios and gaps that expose experience, not volume"),
            dict(labels=area, heading="OSS AREA JOIN", color=TEAL,
                 meta=f"  ·  {len(area)} network features per governorate",
                 subcaption="network reality attached to each subscriber by geography"),
        ],
        f"Feature names read from cem_v3_feature_names.joblib · counts from live PostgreSQL "
        f"({facts['bss_rows']:,} rows, Feb + Mar 2026)",
    )

    oss_raw, oss_derived, oss_area = bucket_oss(facts)
    print(f"  OSS columns  : {len(oss_raw)} raw + {len(oss_derived)} derived")
    print(f"  OSS volume   : {facts['oss_cells']:,} cells over {facts['oss_rows']:,} rows")

    render(
        OUT_DIR / "oss_features.png",
        "OSS Cell Network Features",
        [
            dict(labels=oss_raw, heading="RAW OSS", color=BLUE,
                 meta=f"  ·  {len(oss_raw)} columns  ·  "
                      f"{facts['oss_rows'] / 1e6:.1f}M real cell KPI records",
                 subcaption=f"{facts['oss_cells']:,} cells · signal quality · throughput · "
                            "call drops · cell load · 2G / 3G / 4G"),
            dict(labels=oss_derived, heading="DERIVED", color=ORANGE,
                 meta=f"  ·  {len(oss_derived)} computed KPIs",
                 subcaption="not in the vendor export — computed from integrity, "
                            "throughput and call drops"),
            dict(labels=oss_area, heading="GOVERNORATE AGGREGATE", color=TEAL,
                 meta=f"  ·  {len(oss_area)} area features",
                 subcaption="cell-level KPIs rolled up to the area that joins OSS to BSS"),
        ],
        f"Raw columns read from the live oss_cell_kpis schema · area features from "
        f"cem_v3_feature_names.joblib · {facts['oss_rows']:,} rows",
    )


if __name__ == "__main__":
    main()
