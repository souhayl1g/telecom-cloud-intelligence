"""
Notebook 10 — Granger Feature Selection Gate (Offline)
======================================================

Purpose
-------
Run Granger causality F-tests on candidate (OSS metric, CEM metric) pairs at
the area level over the full historical horizon.  Pairs whose null hypothesis
("OSS does NOT Granger-cause CEM") is rejected at p<0.05 form the **feature
gate** — only Granger-validated OSS metrics are used as features when the
v3 ML models are retrained.

Why this matters for the defense
--------------------------------
Reviewers asked us to flip Granger from a post-hoc explainability widget into
a **causal feature-selection gate** applied BEFORE training.  The two-tier
design implemented here is:

* **Tier 1 (this notebook, offline)** — exhaustive monthly Granger search,
  produces ``granger_feature_gate.json`` listing surviving (oss, cem) tuples
  with their best lag and p-value.  Consumed by the v3 retraining notebooks
  (06/07/08/09) when selecting input features.
* **Tier 2 (online, pipeline-worker)** — cheap per-cycle Granger refresh
  already wired in ``services/pipeline-worker/worker/analytics/granger.py``,
  written to ``granger_causality_results`` for live dashboard explainability.

Outputs
-------
* ``notebooks/granger_feature_gate.json`` — canonical gate file.
* ``services/ai-service/models/granger_gate.json`` — copy used by the
  ai-service at retraining time.
"""

from __future__ import annotations

import json
import os
import shutil
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from statsmodels.tsa.stattools import grangercausalitytests

warnings.filterwarnings("ignore")

# ─── Configuration ──────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "user": os.environ.get("PGUSER", "telecom"),
    "password": os.environ.get("PGPASSWORD", "telecom_pw"),
    "dbname": os.environ.get("PGDATABASE", "telecom_intel"),
}

# Pairs to evaluate.  Format: (oss_metric, cem_metric, expected_direction).
CANDIDATE_PAIRS = [
    ("avg_latency",     "avg_cem_score",     "negative"),
    ("avg_packet_loss", "avg_cem_score",     "negative"),
    ("avg_throughput",  "avg_cem_score",     "positive"),
    ("anomaly_count",   "avg_cem_score",     "negative"),
    ("anomaly_count",   "underserved_pct",   "positive"),
    ("avg_latency",     "underserved_pct",   "positive"),
    ("avg_throughput",  "underserved_pct",   "negative"),
    ("avg_packet_loss", "underserved_pct",   "positive"),
]

MAX_LAG = 3              # months
SIGNIFICANCE = 0.05
MIN_OBS = 4              # months per area required to run the test
OUT_NB = Path(__file__).resolve().parent / "granger_feature_gate.json"
OUT_AI = Path(__file__).resolve().parents[1] / "services" / "ai-service" / "models" / "granger_gate.json"


# ─── Helpers ────────────────────────────────────────────────────────────────
def fetch_monthly_panel() -> pd.DataFrame:
    """Pull the area×month panel used by the Granger engine."""
    sql = """
        SELECT area, month_year,
               avg_throughput, avg_latency, avg_packet_loss,
               anomaly_count, subscriber_count, avg_cem_score,
               underserved_pct, usim_bottleneck_pct
        FROM area_network_health
        WHERE area IS NOT NULL
        ORDER BY area, month_year;
    """
    with psycopg2.connect(**DB_CONFIG) as conn:
        return pd.read_sql(sql, conn)


def best_granger(x: pd.Series, y: pd.Series, max_lag: int) -> dict | None:
    """Return the lag with the lowest p-value for X→Y."""
    if x.std() == 0 or y.std() == 0 or len(x) < max_lag + 2:
        return None
    data = np.column_stack([y.values, x.values])
    try:
        gc = grangercausalitytests(data, maxlag=max_lag, verbose=False)
    except Exception:
        return None

    best = None
    for lag, result in gc.items():
        p = float(result[0]["ssr_ftest"][1])
        f = float(result[0]["ssr_ftest"][0])
        if best is None or p < best["best_pvalue"]:
            best = {"best_lag": int(lag), "best_pvalue": p, "best_fstat": f}
    return best


# ─── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    df = fetch_monthly_panel()
    if df.empty:
        raise SystemExit("area_network_health is empty — run the pipeline first.")

    areas = sorted(df["area"].dropna().unique())
    findings: list[dict] = []

    for oss_metric, cem_metric, expected in CANDIDATE_PAIRS:
        per_area = []
        for area in areas:
            sub = df[df["area"] == area].sort_values("month_year")
            if len(sub) < MIN_OBS:
                continue
            res = best_granger(sub[oss_metric], sub[cem_metric], MAX_LAG)
            if res is None:
                continue
            res.update({"area": area, "significant": res["best_pvalue"] < SIGNIFICANCE})
            per_area.append(res)

        if not per_area:
            continue

        sig_areas = [r for r in per_area if r["significant"]]
        findings.append({
            "oss_metric": oss_metric,
            "cem_metric": cem_metric,
            "expected_direction": expected,
            "areas_tested": len(per_area),
            "areas_significant": len(sig_areas),
            "significance_pct": round(100.0 * len(sig_areas) / len(per_area), 2),
            "mean_best_lag": round(float(np.mean([r["best_lag"] for r in per_area])), 2),
            "median_best_pvalue": round(float(np.median([r["best_pvalue"] for r in per_area])), 4),
            "passes_gate": len(sig_areas) >= max(1, int(0.4 * len(per_area))),
        })

    gate = {
        "schema_version": "1",
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "max_lag_months": MAX_LAG,
        "significance_level": SIGNIFICANCE,
        "min_obs_per_area": MIN_OBS,
        "pairs_evaluated": len(CANDIDATE_PAIRS),
        "areas_evaluated": len(areas),
        "findings": findings,
        "selected_features": [
            f["oss_metric"]
            for f in findings
            if f["passes_gate"]
        ],
    }

    OUT_NB.parent.mkdir(parents=True, exist_ok=True)
    OUT_NB.write_text(json.dumps(gate, indent=2))
    OUT_AI.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT_NB, OUT_AI)

    print(f"[gate] wrote {OUT_NB}")
    print(f"[gate] copied to {OUT_AI}")
    print(f"[gate] {len(gate['selected_features'])} features pass: {gate['selected_features']}")


if __name__ == "__main__":
    main()
