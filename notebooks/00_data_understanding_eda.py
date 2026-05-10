"""
Notebook 00 — Data Understanding & Quality Audit (CRISP-DM Phase 2)
====================================================================

Runs first in numbering order.  Builds the documented evidence reviewers
asked for: cleaning rigor, distributions, correlations, corrupted-row
report, generator-engine validation against real data.

Outputs
-------
* ``notebooks/data/eda/*.png`` — all figures (memoir-ready).
* ``notebooks/data/eda/summary.json`` — machine-readable rollup
  (row counts, NaN %, outlier %, corruption counts, KS p-values, etc.).
* ``notebooks/data/eda/conclusions.md`` — narrative ready to paste into
  CRISP-DM Phase 2 of the memoir.

Run
---
::

    python3 notebooks/00_data_understanding_eda.py
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psycopg2
import seaborn as sns
from scipy.stats import ks_2samp
from sklearn.ensemble import IsolationForest

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight"})

# ─── Configuration ──────────────────────────────────────────────────────────
DB = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "user": os.environ.get("PGUSER", "telecom"),
    "password": os.environ.get("PGPASSWORD", "telecom_pw"),
    "dbname": os.environ.get("PGDATABASE", "telecom_intel"),
}

OUT = Path(__file__).resolve().parent / "data" / "eda"
OUT.mkdir(parents=True, exist_ok=True)

REAL_BSS_MONTHS = {"2026-02", "2026-03"}                       # Feb + Mar
SIM_BSS_MONTHS = {"2026-01", "2026-04", "2026-05"}              # Jan + Apr + May
REAL_OSS_MONTHS = {"2026-03", "2026-04"}
SIM_OSS_MONTHS = {"2026-01", "2026-02", "2026-05", "2026-06"}

CEM_FEATURES = [
    "usim_bottleneck", "data_intensity", "dou_total", "duration",
    "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
    "throughput_mbps", "latency_ms", "packet_loss_rate",
    "cell_load_pct",
]
SUMMARY: dict = {"sections": {}}


# ─── Loaders ────────────────────────────────────────────────────────────────
def load_bss(limit: int = 200_000) -> pd.DataFrame:
    sql = f"""
        SELECT imsi_hash, area, generation, usertype, highest_rat,
               dou_total, traffic_2g, traffic_3g, traffic_4g, traffic_5g,
               duration, s1_mme_sr, iu_attach_sr, gb_attach_sr,
               session_flag, month_year, churned
        FROM bss_subscribers
        ORDER BY random()
        LIMIT {limit};
    """
    with psycopg2.connect(**DB) as conn:
        return pd.read_sql(sql, conn)


def load_oss(limit: int = 200_000) -> pd.DataFrame:
    sql = f"""
        SELECT cell_id, area, month_year,
               throughput_mbps, latency_ms, packet_loss_rate, jitter_ms,
               cell_load_pct, rsrp_dbm, active_users, anomaly_flag, created_at
        FROM oss_cell_kpis
        ORDER BY random()
        LIMIT {limit};
    """
    with psycopg2.connect(**DB) as conn:
        return pd.read_sql(sql, conn)


def load_features(limit: int = 200_000) -> pd.DataFrame:
    sql = f"""
        SELECT imsi_hash, month_year, rat_gap_score, usim_bottleneck,
               data_intensity, network_experience_index,
               cem_score, cem_score_target, churn_risk_flag, churned
        FROM subscriber_features
        ORDER BY random()
        LIMIT {limit};
    """
    with psycopg2.connect(**DB) as conn:
        return pd.read_sql(sql, conn)


# ─── Section 1 — Source Inventory ───────────────────────────────────────────
def section_inventory(bss: pd.DataFrame, oss: pd.DataFrame, feats: pd.DataFrame) -> None:
    inv = {
        "bss_rows_sampled": len(bss),
        "oss_rows_sampled": len(oss),
        "features_rows_sampled": len(feats),
        "bss_months": sorted(bss["month_year"].dropna().unique().tolist()),
        "oss_months": sorted(oss["month_year"].dropna().unique().tolist()),
        "bss_real_vs_simulated": {
            "real": int(bss["month_year"].isin(REAL_BSS_MONTHS).sum()),
            "simulated": int(bss["month_year"].isin(SIM_BSS_MONTHS).sum()),
        },
        "oss_real_vs_simulated": {
            "real": int(oss["month_year"].isin(REAL_OSS_MONTHS).sum()),
            "simulated": int(oss["month_year"].isin(SIM_OSS_MONTHS).sum()),
        },
    }
    SUMMARY["sections"]["1_inventory"] = inv

    # Bar plot: rows per month (BSS + OSS).
    months = sorted(set(bss["month_year"].dropna()) | set(oss["month_year"].dropna()))
    bss_counts = [int((bss["month_year"] == m).sum()) for m in months]
    oss_counts = [int((oss["month_year"] == m).sum()) for m in months]
    fig, ax = plt.subplots(figsize=(10, 4))
    width = 0.4
    x = np.arange(len(months))
    ax.bar(x - width / 2, bss_counts, width, label="BSS")
    ax.bar(x + width / 2, oss_counts, width, label="OSS")
    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=30)
    ax.set_ylabel("Rows sampled")
    ax.set_title("Section 1 — Sampled rows per month (real + simulated)")
    ax.legend()
    fig.savefig(OUT / "01_inventory.png")
    plt.close(fig)


# ─── Section 2 — Missingness ────────────────────────────────────────────────
def section_missingness(bss: pd.DataFrame, oss: pd.DataFrame) -> None:
    nan_bss = bss.isna().mean().sort_values(ascending=False)
    nan_oss = oss.isna().mean().sort_values(ascending=False)

    SUMMARY["sections"]["2_missingness"] = {
        "bss_top_nan_pct": {k: round(float(v) * 100, 2) for k, v in nan_bss.head(8).items()},
        "oss_top_nan_pct": {k: round(float(v) * 100, 2) for k, v in nan_oss.head(8).items()},
    }

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.heatmap(bss.isna().head(500), cbar=False, ax=axes[0], cmap="rocket_r")
    axes[0].set_title("BSS missingness (first 500 rows)")
    sns.heatmap(oss.isna().head(500), cbar=False, ax=axes[1], cmap="rocket_r")
    axes[1].set_title("OSS missingness (first 500 rows)")
    fig.savefig(OUT / "02_missingness.png")
    plt.close(fig)


# ─── Section 3 — Distributions ──────────────────────────────────────────────
def section_distributions(bss: pd.DataFrame, oss: pd.DataFrame, feats: pd.DataFrame) -> None:
    cols_bss = ["dou_total", "duration", "s1_mme_sr", "iu_attach_sr", "gb_attach_sr"]
    cols_oss = ["throughput_mbps", "latency_ms", "packet_loss_rate", "cell_load_pct", "rsrp_dbm"]
    cols_feat = ["data_intensity", "network_experience_index", "cem_score", "rat_gap_score"]

    def grid(df: pd.DataFrame, cols: list[str], title: str, path: Path) -> None:
        fig, axes = plt.subplots(1, len(cols), figsize=(4 * len(cols), 3.5))
        if len(cols) == 1:
            axes = [axes]
        for ax, col in zip(axes, cols):
            data = df[col].dropna().astype(float)
            if data.empty:
                ax.set_title(f"{col} (empty)")
                continue
            sns.histplot(data, kde=True, ax=ax, bins=40, color="#6366f1")
            ax.set_title(col)
        fig.suptitle(title)
        fig.savefig(path)
        plt.close(fig)

    grid(bss, cols_bss, "Section 3a — BSS distributions", OUT / "03a_bss_dist.png")
    grid(oss, cols_oss, "Section 3b — OSS distributions", OUT / "03b_oss_dist.png")
    grid(feats, cols_feat, "Section 3c — Engineered feature distributions", OUT / "03c_feat_dist.png")

    SUMMARY["sections"]["3_distributions"] = {
        "bss_columns_plotted": cols_bss,
        "oss_columns_plotted": cols_oss,
        "feature_columns_plotted": cols_feat,
    }


# ─── Section 4 — Outliers ───────────────────────────────────────────────────
def section_outliers(oss: pd.DataFrame) -> None:
    cols = ["throughput_mbps", "latency_ms", "packet_loss_rate", "cell_load_pct"]
    iqr_pct = {}
    for c in cols:
        s = oss[c].dropna().astype(float)
        if s.empty:
            iqr_pct[c] = 0.0
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        iqr_pct[c] = round(float(((s < lo) | (s > hi)).mean()) * 100, 2)

    iso = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
    sub = oss[cols].dropna()
    if not sub.empty:
        flags = iso.fit_predict(sub.values)
        iso_pct = round(float((flags == -1).mean()) * 100, 2)
    else:
        iso_pct = 0.0

    SUMMARY["sections"]["4_outliers"] = {
        "iqr_pct_per_column": iqr_pct,
        "isolation_forest_pct_overall": iso_pct,
    }

    fig, axes = plt.subplots(1, len(cols), figsize=(4 * len(cols), 3.5))
    for ax, c in zip(axes, cols):
        data = oss[c].dropna().astype(float)
        sns.boxplot(x=data, ax=ax, color="#a78bfa")
        ax.set_title(f"{c}\nIQR outliers: {iqr_pct[c]}%")
    fig.suptitle("Section 4 — OSS outlier audit (IQR + IsolationForest)")
    fig.savefig(OUT / "04_outliers.png")
    plt.close(fig)


# ─── Section 5 — Correlations ───────────────────────────────────────────────
def section_correlations(oss: pd.DataFrame, feats: pd.DataFrame) -> None:
    cols_oss = ["throughput_mbps", "latency_ms", "packet_loss_rate", "cell_load_pct", "rsrp_dbm"]
    cols_feat = ["data_intensity", "network_experience_index", "cem_score", "rat_gap_score"]

    pearson_oss = oss[cols_oss].corr(method="pearson")
    spearman_oss = oss[cols_oss].corr(method="spearman")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    sns.heatmap(pearson_oss, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=axes[0])
    axes[0].set_title("OSS Pearson")
    sns.heatmap(spearman_oss, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=axes[1])
    axes[1].set_title("OSS Spearman")
    fig.savefig(OUT / "05a_oss_corr.png")
    plt.close(fig)

    pearson_feat = feats[cols_feat].corr(method="pearson")
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(pearson_feat, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Engineered features — Pearson correlation")
    fig.savefig(OUT / "05b_feat_corr.png")
    plt.close(fig)

    SUMMARY["sections"]["5_correlations"] = {
        "oss_strongest_pair": _top_corr(pearson_oss),
        "feature_strongest_pair": _top_corr(pearson_feat),
    }


def _top_corr(corr: pd.DataFrame) -> dict:
    triu = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1))
    triu = triu.abs().stack().sort_values(ascending=False)
    if triu.empty:
        return {}
    pair = triu.index[0]
    return {"pair": list(pair), "abs_corr": round(float(triu.iloc[0]), 4)}


# ─── Section 6 — Corrupted Rows ─────────────────────────────────────────────
def section_corruption(bss: pd.DataFrame) -> None:
    issues = {
        "negative_dou": int((bss["dou_total"] < 0).sum()),
        "negative_duration": int((bss["duration"] < 0).sum()),
        "traffic_above_1.5x_dou": int(
            (
                bss[["traffic_2g", "traffic_3g", "traffic_4g", "traffic_5g"]].fillna(0).sum(axis=1)
                > 1.5 * bss["dou_total"].fillna(0)
            ).sum()
        ),
        "imsi_invalid_length": int((bss["imsi_hash"].astype(str).str.len() < 32).sum()),
        "future_month_year": int((bss["month_year"].astype(str) > "2026-12").sum()),
        "missing_area": int(bss["area"].isna().sum()),
        "attach_sr_above_one": int(
            ((bss["s1_mme_sr"] > 1.0) | (bss["iu_attach_sr"] > 1.0) | (bss["gb_attach_sr"] > 1.0)).sum()
        ),
    }
    SUMMARY["sections"]["6_corruption"] = issues


# ─── Section 7 — Class Imbalance ────────────────────────────────────────────
def section_imbalance(feats: pd.DataFrame) -> None:
    rat_under = float((feats["rat_gap_score"] > 0.3).mean()) if "rat_gap_score" in feats else 0.0
    churn_rate = float(feats["churned"].fillna(False).astype(int).mean()) if "churned" in feats else 0.0
    SUMMARY["sections"]["7_imbalance"] = {
        "rat_underservice_positive_rate_pct": round(rat_under * 100, 2),
        "churn_positive_rate_pct": round(churn_rate * 100, 2),
        "expected_rat_pct_per_claude_md": 9.2,
    }


# ─── Section 8 — Temporal Drift ─────────────────────────────────────────────
def section_drift(bss: pd.DataFrame) -> None:
    months = sorted(bss["month_year"].dropna().unique())
    if len(months) < 2:
        SUMMARY["sections"]["8_drift"] = {"status": "not_enough_months"}
        return

    drift = []
    for prev, curr in zip(months, months[1:]):
        a = bss.loc[bss["month_year"] == prev, "dou_total"].dropna()
        b = bss.loc[bss["month_year"] == curr, "dou_total"].dropna()
        if len(a) > 50 and len(b) > 50:
            stat, p = ks_2samp(a, b)
            drift.append({
                "from": prev,
                "to": curr,
                "ks_statistic": round(float(stat), 4),
                "p_value": round(float(p), 6),
                "drift_significant": bool(p < 0.05),
            })
    SUMMARY["sections"]["8_drift"] = {"dou_total_ks_tests": drift}

    if drift:
        labels = [f"{d['from']} → {d['to']}" for d in drift]
        stats = [d["ks_statistic"] for d in drift]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(labels, stats, color="#f97316")
        ax.set_ylabel("KS statistic on dou_total")
        ax.set_title("Section 8 — Temporal drift (consecutive month KS)")
        plt.xticks(rotation=20)
        fig.savefig(OUT / "08_drift.png")
        plt.close(fig)


# ─── Section 9 — Generator Validation (real vs simulated overlay) ───────────
def section_generator(bss: pd.DataFrame) -> None:
    real = bss.loc[bss["month_year"].isin(REAL_BSS_MONTHS), "dou_total"].dropna()
    sim = bss.loc[bss["month_year"].isin(SIM_BSS_MONTHS), "dou_total"].dropna()
    if real.empty or sim.empty:
        SUMMARY["sections"]["9_generator"] = {"status": "real_or_simulated_missing"}
        return

    stat, p = ks_2samp(real, sim)
    SUMMARY["sections"]["9_generator"] = {
        "ks_statistic_real_vs_sim_dou": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "interpretation": (
            "p < 0.05 → distributions differ — expected because simulator applies temporal drift "
            "(Jan -12% DOU, Apr +18%, May +35%). Drift IS the design intent, not a quality bug."
        ),
    }

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.kdeplot(np.log1p(real), label="Real (Feb+Mar)", ax=ax, color="#10b981", linewidth=2)
    sns.kdeplot(np.log1p(sim), label="Simulated (Jan+Apr+May)", ax=ax, color="#a78bfa", linewidth=2)
    ax.set_xlabel("log(1 + dou_total)")
    ax.set_title("Section 9 — Real vs Simulated overlay (BSS dou_total)")
    ax.legend()
    fig.savefig(OUT / "09_generator_overlay.png")
    plt.close(fig)


# ─── Section 10 — Conclusions ───────────────────────────────────────────────
def section_conclusions() -> None:
    md_path = OUT / "conclusions.md"
    parts = ["# CRISP-DM Phase 2 — Data Understanding Conclusions", ""]
    parts.append("Generated by ``notebooks/00_data_understanding_eda.py``. "
                 "Paste these blocks directly into the memoir.")
    parts.append("")
    for key, payload in SUMMARY["sections"].items():
        parts.append(f"## {key.replace('_', ' ').title()}")
        parts.append("```json")
        parts.append(json.dumps(payload, indent=2, default=str))
        parts.append("```")
        parts.append("")

    md_path.write_text("\n".join(parts))
    (OUT / "summary.json").write_text(json.dumps(SUMMARY, indent=2, default=str))


# ─── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    print("[eda] loading data ...")
    bss = load_bss()
    oss = load_oss()
    feats = load_features()
    print(f"[eda] sampled BSS={len(bss)} OSS={len(oss)} features={len(feats)}")

    steps = [
        ("inventory", lambda: section_inventory(bss, oss, feats)),
        ("missingness", lambda: section_missingness(bss, oss)),
        ("distributions", lambda: section_distributions(bss, oss, feats)),
        ("outliers", lambda: section_outliers(oss)),
        ("correlations", lambda: section_correlations(oss, feats)),
        ("corruption", lambda: section_corruption(bss)),
        ("imbalance", lambda: section_imbalance(feats)),
        ("drift", lambda: section_drift(bss)),
        ("generator", lambda: section_generator(bss)),
        ("conclusions", section_conclusions),
    ]
    for i, (name, fn) in enumerate(steps, start=1):
        print(f"[eda] section {i} — {name}")
        fn()

    print(f"[eda] outputs: {OUT}/")
    print(f"[eda] PNGs: {len(list(OUT.glob('*.png')))}, summary.json + conclusions.md written")


if __name__ == "__main__":
    main()
