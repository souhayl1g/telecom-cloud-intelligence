"""Notebook Lab (Data Scientist surface).

Surfaces the notebook WORK as rendered OUTPUTS inside the dashboard — Jupyter can't
be rebuilt natively, so we render the model cards + training summary + metrics the
notebooks produced (mounted at /notebooks/models). No live kernel; honest artifacts.
"""

import json
import os

from fastapi import APIRouter, Depends

from auth import require_role

router = APIRouter()

MODELS_DIR = os.getenv("MODELS_DIR", "/notebooks/models")

# Static catalogue of the 6 notebooks (purpose only — the heavy outputs are the cards).
_NOTEBOOKS = [
    {
        "name": "00_data_understanding_eda",
        "title": "Data Understanding & EDA",
        "purpose": "Geo choropleths, topology, missingness, KDE/IQR/violin, z-score outliers.",
    },
    {
        "name": "01_etl_feature_engineering",
        "title": "ETL & Feature Engineering",
        "purpose": "Clean → type → dedupe → engineer the curated CEM feature tables.",
    },
    {
        "name": "02_cem_score_training",
        "title": "CEM Score — LightGBM (DART)",
        "purpose": "Experience score regressor; SHAP, calibration, CV honesty checks.",
    },
    {
        "name": "03_oss_vae_anomaly_training",
        "title": "OSS Experience Anomaly — VAE",
        "purpose": "PyTorch VAE on normal-only OSS; ROC/PR, latent PCA, threshold sweep.",
    },
    {
        "name": "04_rat_underservice_training",
        "title": "RAT Underservice — XGBoost",
        "purpose": "Per-subscriber RAT-gap classifier; leakage fix, F1 sweep, GPU.",
    },
    {
        "name": "10_granger_feature_selection",
        "title": "Granger Feature Gate",
        "purpose": "ADF/KPSS stationarity + Granger F-test → offline feature gate.",
    },
]


def _read(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


@router.get("/notebooks/lab")
def notebook_lab(user=Depends(require_role("data_scientist"))):
    """Notebook catalogue + rendered model cards + training summary + metrics."""
    cards = []
    try:
        for fname in sorted(os.listdir(MODELS_DIR)):
            if fname.endswith("_model_card.md"):
                md = _read(os.path.join(MODELS_DIR, fname))
                if md:
                    cards.append(
                        {"model": fname.replace("_model_card.md", ""), "markdown": md}
                    )
    except Exception:
        pass

    summary = _read(os.path.join(MODELS_DIR, "master_v3_training_summary.md"))
    metrics = None
    raw = _read(os.path.join(MODELS_DIR, "metrics.json"))
    if raw:
        try:
            metrics = json.loads(raw)
        except Exception:
            metrics = None

    return {
        "notebooks": _NOTEBOOKS,
        "cards": cards,
        "summary_markdown": summary,
        "metrics": metrics,
    }
