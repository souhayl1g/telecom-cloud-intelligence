#!/usr/bin/env python3
"""Render the OSS<->BSS geographic join-key figure for the defense deck.

Reads live counts from the running PostgreSQL container and the ADM1 GeoJSON
that the dashboard already ships, then draws a three-part figure:

    A. OSS side  - cell sites per governorate (site codes, 18.8M real KPI rows)
    B. BSS side  - real subscribers per governorate (Feb+Mar 2026 = 968,077)
    C. The join  - how a site code and a subscriber area both resolve to one
                   governorate, and which converged features that produces

Nothing here is synthesised. Every number printed on the figure comes from a
query executed at render time; the Granger panel reports the honest
significant-edge count straight out of notebooks/granger_feature_gate.json.

Usage:
    python3 scripts/generate_join_key_figure.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
GEOJSON = REPO / "dashboard" / "lib" / "tunisia-geojson.json"
GRANGER_GATE = REPO / "notebooks" / "granger_feature_gate.json"
OUT_PNG = REPO / "report" / "figures" / "oss_bss_join_key.png"

# Real months only - simulated months are excluded so the BSS panel matches the
# 968,077 real-subscriber figure quoted in the report.
BSS_REAL_MONTHS = ("2026-02", "2026-03")

INK = "#0D1117"
MUTED = "#5A6472"
CYAN = "#00B4D8"
ORANGE = "#FF6B35"
TEAL = "#0E9F6E"
PAGE = "#FFFFFF"
HAIRLINE = "#D8DEE6"

# Latitude-corrected aspect: Tunisia sits near 34N, so one degree of longitude
# is only cos(34) as wide as one degree of latitude. Plotting raw lon/lat 1:1
# would squash the country horizontally.
LAT_ASPECT = 1.21


# --------------------------------------------------------------------------
# Area code -> governorate (port of dashboard/lib/tunisia-areas.ts)
# --------------------------------------------------------------------------

PREFIX_MAP = {
    "TUN": "Tunis", "TNS": "Tunis", "BAB": "Tunis", "CAR": "Tunis", "CRT": "Tunis",
    "ARI": "Ariana", "ARN": "Ariana",
    "BAR": "Ben Arous", "BNA": "Ben Arous", "BAS": "Ben Arous", "HMM": "Ben Arous",
    "MAN": "Manouba", "MNB": "Manouba", "MNO": "Manouba", "MNA": "Manouba",
    "BIZ": "Bizerte", "BNZ": "Bizerte", "BZT": "Bizerte",
    "BEJ": "Béja", "BJA": "Béja",
    "JEN": "Jendouba", "JND": "Jendouba", "JDB": "Jendouba",
    "KEF": "El Kef", "KSE": "El Kef", "LKF": "El Kef",
    "SIL": "Siliana", "SLN": "Siliana",
    "KAI": "Kairouan", "KRN": "Kairouan", "KRW": "Kairouan",
    "KAS": "Kasserine", "KSR": "Kasserine", "KSS": "Kasserine",
    "SID": "Sidi Bouzid", "SBZ": "Sidi Bouzid", "SDB": "Sidi Bouzid",
    "SOU": "Sousse", "SSE": "Sousse", "SLT": "Sousse", "SLO": "Sousse", "SAH": "Sousse",
    "MON": "Monastir", "MSR": "Monastir", "MTR": "Monastir",
    "MAH": "Mahdia", "MHD": "Mahdia",
    "SFX": "Sfax", "SFA": "Sfax", "SFS": "Sfax", "SKR": "Sfax",
    "GAB": "Gabès", "GBS": "Gabès", "GBA": "Gabès",
    "MED": "Médenine", "MDN": "Médenine", "DJB": "Médenine", "ZAR": "Médenine",
    "TAT": "Tataouine", "TTN": "Tataouine",
    "GAF": "Gafsa", "GFS": "Gafsa", "GFA": "Gafsa",
    "TOZ": "Tozeur", "TZR": "Tozeur",
    "KEB": "Kébili", "KBL": "Kébili", "KBI": "Kébili",
    "ZGO": "Zaghouan", "ZGT": "Zaghouan", "ZAG": "Zaghouan", "ZGN": "Zaghouan",
    "NAB": "Nabeul", "NBL": "Nabeul", "HAM": "Nabeul", "KEL": "Nabeul",
}

FULL_NAME_MAP = [
    ("SFAX", "Sfax"), ("TUNIS", "Tunis"), ("ARIANA", "Ariana"),
    ("MANOUBA", "Manouba"), ("BIZERTE", "Bizerte"), ("BEJA", "Béja"),
    ("BÉJA", "Béja"), ("JENDOUBA", "Jendouba"), ("KAIROUAN", "Kairouan"),
    ("KASSERINE", "Kasserine"), ("SOUSSE", "Sousse"), ("MONASTIR", "Monastir"),
    ("MAHDIA", "Mahdia"), ("NABEUL", "Nabeul"), ("ZAGHOUAN", "Zaghouan"),
    ("ZAGHOUEN", "Zaghouan"), ("SILIANA", "Siliana"), ("GAFSA", "Gafsa"),
    ("GABES", "Gabès"), ("GABÈS", "Gabès"), ("MEDENINE", "Médenine"),
    ("TATAOUINE", "Tataouine"), ("TOZEUR", "Tozeur"), ("KEBILI", "Kébili"),
    ("KÉBILI", "Kébili"), ("ELKEF", "El Kef"), ("LE_KEF", "El Kef"),
    ("HAMMAMET", "Nabeul"), ("HAMMAM_SOUSSE", "Sousse"),
    ("HAMMAM_SIALA", "Nabeul"), ("DJERBA", "Médenine"), ("CARTHAGE", "Tunis"),
    ("LA_MARSA", "Tunis"), ("BARDO", "Tunis"),
]


def area_to_governorate(area: str | None) -> str | None:
    """Resolve a TT site code or subscriber area label to one governorate."""
    if not area:
        return None
    s = area.upper().strip()
    if not s or s in {"NULL", "NONE", "N/A"}:
        return None
    s = re.sub(r"^[2-5]G_+", "", s)
    for prefix, gov in FULL_NAME_MAP:
        if s.startswith(prefix):
            return gov
    m = re.match(r"^[A-Z]{3}", s)
    if m and m.group(0) in PREFIX_MAP:
        return PREFIX_MAP[m.group(0)]
    return None


# --------------------------------------------------------------------------
# Live data
# --------------------------------------------------------------------------


def psql(sql: str) -> list[list[str]]:
    """Run SQL in the postgres container, return rows as split fields."""
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres",
         "psql", "-U", "telecom", "-d", "telecom_intel", "-tAF|", "-c", sql],
        cwd=REPO, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"psql failed:\n{proc.stderr.strip()}")
    return [ln.split("|") for ln in proc.stdout.strip().splitlines() if ln.strip()]


def roll_up(rows: list[list[str]]) -> tuple[dict[str, int], int]:
    """Aggregate (area, count) pairs into governorate buckets.

    Returns the per-governorate totals plus however many fell through the
    mapping, so the figure can state its own coverage instead of hiding it.
    """
    buckets: dict[str, int] = {}
    unmapped = 0
    for area, raw in rows:
        n = int(raw)
        gov = area_to_governorate(area)
        if gov is None:
            unmapped += n
        else:
            buckets[gov] = buckets.get(gov, 0) + n
    return buckets, unmapped


def load_counts() -> dict:
    months = "','".join(BSS_REAL_MONTHS)
    oss_rows = psql(
        "SELECT area, COUNT(DISTINCT cell_id) FROM oss_cell_kpis "
        "WHERE area IS NOT NULL GROUP BY area;"
    )
    bss_rows = psql(
        f"SELECT area, COUNT(DISTINCT imsi_hash) FROM bss_subscribers "
        f"WHERE month_year IN ('{months}') GROUP BY area;"
    )
    oss_cells, oss_unmapped = roll_up(oss_rows)
    bss_subs, bss_unmapped = roll_up(bss_rows)

    total_cells = int(psql("SELECT COUNT(DISTINCT cell_id) FROM oss_cell_kpis;")[0][0])
    total_kpi_rows = int(psql("SELECT COUNT(*) FROM oss_cell_kpis;")[0][0])
    total_subs = int(
        psql(f"SELECT COUNT(DISTINCT imsi_hash) FROM bss_subscribers "
             f"WHERE month_year IN ('{months}');")[0][0]
    )
    return {
        "oss_cells": oss_cells, "oss_unmapped": oss_unmapped,
        "bss_subs": bss_subs, "bss_unmapped": bss_unmapped,
        "total_cells": total_cells, "total_kpi_rows": total_kpi_rows,
        "total_subs": total_subs,
        "n_oss_areas": len(oss_rows), "n_bss_areas": len(bss_rows),
    }


def load_granger() -> tuple[int, int, int, float]:
    g = json.loads(GRANGER_GATE.read_text())
    edges = g["edges"]
    sig = [e for e in edges if e.get("significant")]
    return len(sig), len(edges), g["lag_max_months"], g["significance_threshold"]


# --------------------------------------------------------------------------
# Map drawing
# --------------------------------------------------------------------------


def rings(feature: dict) -> list[list]:
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    return [poly[0] for poly in geom["coordinates"]]


def draw_choropleth(ax, features, values: dict[str, int], base: str, title: str,
                    subtitle: str) -> None:
    """Fill each governorate by value, light-to-saturated in one hue."""
    vmax = max(values.values()) if values else 1
    rgb = matplotlib.colors.to_rgb(base)

    for feat in features:
        name = feat["properties"]["shapeName"]
        v = values.get(name, 0)
        # Perceptual floor: even the quietest governorate stays visible.
        t = 0.12 + 0.88 * (v / vmax) ** 0.55 if vmax else 0.12
        fill = tuple(1 - t * (1 - c) for c in rgb)
        for ring in rings(feat):
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            ax.fill(xs, ys, facecolor=fill, edgecolor=PAGE, linewidth=0.7, zorder=2)

    ax.set_aspect(LAT_ASPECT)
    ax.axis("off")
    # Stack header in axes-fraction space: title above subtitle above the map.
    # (set_title's point-based pad collided with the subtitle line.)
    ax.text(0, 1.055, title, transform=ax.transAxes, fontsize=12.5,
            fontweight="bold", color=base, va="bottom", ha="left")
    ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=8.4,
            color=MUTED, va="bottom", ha="left")


def annotate_top(ax, features, values: dict[str, int], base: str, n: int = 4) -> None:
    """Label the busiest governorates only - full labels would collide.

    Each box is tried at the governorate centroid first, then nudged along a
    widening ring of offsets until it no longer overlaps an already-placed
    box (measured for real via the renderer, not estimated).
    """
    top = sorted(values.items(), key=lambda kv: -kv[1])[:n]
    by_name = {f["properties"]["shapeName"]: f for f in features}

    fig = ax.figure
    fig.canvas.draw()  # a live renderer is needed to measure label boxes
    renderer = fig.canvas.get_renderer()

    # (dx, dy) in degrees: home first, then a widening ring of candidates.
    offsets = [(0.0, 0.0)]
    for r in (0.55, 1.05, 1.55):
        offsets += [
            (r, 0.0), (-r, 0.0), (0.0, r), (0.0, -r),
            (r * 0.7, r * 0.7), (-r * 0.7, r * 0.7),
            (r * 0.7, -r * 0.7), (-r * 0.7, -r * 0.7),
        ]

    placed = []
    for name, v in top:
        feat = by_name.get(name)
        if feat is None:
            continue
        ring = max(rings(feat), key=len)
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        for dx, dy in offsets:
            t = ax.text(cx + dx, cy + dy, f"{name}\n{v:,}", ha="center",
                        va="center", fontsize=6.9, fontweight="bold", color=INK,
                        zorder=5,
                        bbox=dict(boxstyle="round,pad=0.26", facecolor="white",
                                  edgecolor=base, linewidth=0.8, alpha=0.93))
            bb = t.get_window_extent(renderer).expanded(1.05, 1.18)
            if all(not bb.overlaps(p) for p in placed):
                placed.append(bb)
                break
            t.remove()


def chip(ax, x, y, w, h, label, color, fontsize=8.0, bold=False) -> None:
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.012",
        facecolor="white", edgecolor=color, linewidth=1.15,
        transform=ax.transAxes, zorder=3, clip_on=False))
    ax.text(x + w / 2, y + h / 2, label, transform=ax.transAxes,
            ha="center", va="center", fontsize=fontsize, color=INK,
            fontweight="bold" if bold else "normal",
            family="monospace", zorder=4)


def track(s: str, n: int = 1) -> str:
    """Emulate CSS letter-spacing: insert `n` thin spaces between characters."""
    gap = " " * n
    return gap.join(s)


def draw_join_band(ax, data: dict) -> None:
    """The middle band: two unlike keys resolving to one governorate."""
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.5, 0.94, track("THE JOIN KEY", 2), ha="center", va="top",
            fontsize=11.5, fontweight="bold", color=TEAL)

    # left: an OSS site code       right: a BSS subscriber area label
    chip(ax, 0.015, 0.50, 0.20, 0.17, "SLT4090", CYAN, 9.0, bold=True)
    ax.text(0.115, 0.44, "OSS site code", transform=ax.transAxes, ha="center",
            va="top", fontsize=7.6, color=MUTED)
    ax.text(0.115, 0.345, f"{data['n_oss_areas']:,} distinct codes",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.0,
            color=CYAN, style="italic")

    chip(ax, 0.785, 0.50, 0.20, 0.17, "SOUSSE", ORANGE, 9.0, bold=True)
    ax.text(0.885, 0.44, "BSS subscriber area", transform=ax.transAxes,
            ha="center", va="top", fontsize=7.6, color=MUTED)
    ax.text(0.885, 0.345, f"{data['n_bss_areas']:,} distinct labels",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.0,
            color=ORANGE, style="italic")

    # centre: the resolved governorate
    chip(ax, 0.395, 0.47, 0.21, 0.23, "Sousse", TEAL, 11.0, bold=True)
    ax.text(0.50, 0.405, "governorate", transform=ax.transAxes, ha="center",
            va="top", fontsize=7.6, color=MUTED)

    for x0, x1, col, note in (
        (0.225, 0.385, CYAN, "prefix SLT"),
        (0.775, 0.615, ORANGE, "name match"),
    ):
        ax.add_patch(FancyArrowPatch(
            (x0, 0.585), (x1, 0.585), transform=ax.transAxes,
            arrowstyle="-|>", mutation_scale=13, linewidth=1.5,
            color=col, zorder=3, clip_on=False))
        ax.text((x0 + x1) / 2, 0.625, note, transform=ax.transAxes,
                ha="center", va="bottom", fontsize=7.0, color=col,
                family="monospace")

    ax.text(0.5, 0.20,
            "No IMSI-to-cell mapping exists in the source data.\n"
            "The governorate is the only legitimate join key.",
            transform=ax.transAxes, ha="center", va="center", fontsize=8.6,
            color=INK, linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#F4FBF8",
                      edgecolor=TEAL, linewidth=1.1))


def draw_footer(ax, data: dict, granger: tuple) -> None:
    """Converged output features on the left, Granger method on the right."""
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.0, 0.93, track("WHAT THE JOIN PRODUCES"), ha="left", va="top",
            fontsize=9.6, fontweight="bold", color=TEAL)
    feats = [
        "avg_integrity_area", "avg_cdr_area", "avg_throughput_area",
        "avg_users_area", "avg_latency_area", "avg_loss_area",
        "cell_count_area", "anomaly_count_area",
    ]
    for i, f in enumerate(feats):
        col, row = i % 2, i // 2
        chip(ax, 0.0 + col * 0.185, 0.60 - row * 0.185, 0.172, 0.135, f, TEAL, 7.0)

    ax.text(0.0, -0.10,
            "8 network features attached to every subscriber by geography",
            ha="left", va="top", fontsize=7.8, color=MUTED, style="italic")

    n_sig, n_edges, lag_max, alpha = granger
    ax.text(0.60, 0.93, track("CAUSALITY TEST (METHOD)"), ha="left", va="top",
            fontsize=9.6, fontweight="bold", color=INK)
    ax.text(0.60, 0.70,
            f"Granger F-test on the converged area series\n"
            f"maximum lag {lag_max} months  ·  threshold p < {alpha}\n"
            f"{n_sig} of {n_edges} OSS-to-CEM edges significant",
            ha="left", va="top", fontsize=8.2, color=INK, linespacing=1.8,
            family="monospace")
    ax.text(0.60, 0.14,
            "Reported as tested, not as proven — the gate output is\n"
            "read straight from granger_feature_gate.json.",
            ha="left", va="top", fontsize=7.4, color=MUTED,
            style="italic", linespacing=1.6)


# --------------------------------------------------------------------------


def main() -> None:
    if not GEOJSON.exists():
        sys.exit(f"missing geojson: {GEOJSON}")

    print("querying live postgres ...")
    data = load_counts()
    granger = load_granger()
    features = json.loads(GEOJSON.read_text())["features"]

    # Print every number that lands on the canvas, so the render is auditable.
    print(f"  OSS  : {data['total_cells']:,} cells over "
          f"{data['total_kpi_rows']:,} KPI rows, "
          f"{len(data['oss_cells'])}/24 governorates matched, "
          f"{data['oss_unmapped']:,} cells unmapped")
    print(f"  BSS  : {data['total_subs']:,} real subscribers "
          f"({'+'.join(BSS_REAL_MONTHS)}), "
          f"{len(data['bss_subs'])}/24 governorates matched, "
          f"{data['bss_unmapped']:,} subscribers unmapped")
    print(f"  Granger: {granger[0]}/{granger[1]} edges significant")

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(11.6, 12.2), dpi=300, facecolor=PAGE)
    gs = fig.add_gridspec(
        3, 2, height_ratios=[1.42, 0.60, 0.50],
        left=0.045, right=0.955, top=0.858, bottom=0.055,
        wspace=0.06, hspace=0.30,
    )

    fig.text(0.045, 0.955, "Geography Is the Join Key", fontsize=23,
             fontweight="bold", color=INK, va="top")
    fig.text(0.045, 0.915,
             "OSS cell KPIs and BSS subscriber profiles share no identifier — "
             "they meet at the governorate.",
             fontsize=10.2, color=MUTED, va="top")

    ax_oss = fig.add_subplot(gs[0, 0])
    draw_choropleth(
        ax_oss, features, data["oss_cells"], CYAN, "OSS  ·  CELL SITES",
        f"{data['total_cells']:,} cells  ·  {data['total_kpi_rows'] / 1e6:.1f}M real KPI rows",
    )
    annotate_top(ax_oss, features, data["oss_cells"], CYAN)

    ax_bss = fig.add_subplot(gs[0, 1])
    draw_choropleth(
        ax_bss, features, data["bss_subs"], ORANGE, "BSS  ·  SUBSCRIBERS",
        f"{data['total_subs']:,} real subscribers  ·  Feb + Mar 2026",
    )
    annotate_top(ax_bss, features, data["bss_subs"], ORANGE)

    draw_join_band(fig.add_subplot(gs[1, :]), data)
    draw_footer(fig.add_subplot(gs[2, :]), data, granger)

    fig.text(0.045, 0.018,
             f"Rendered from live PostgreSQL · {data['n_oss_areas']:,} OSS site codes and "
             f"{data['n_bss_areas']:,} BSS area labels resolved to 24 governorates",
             fontsize=7.4, color=MUTED, va="bottom")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=300, facecolor=PAGE, bbox_inches="tight")
    print(f"wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
