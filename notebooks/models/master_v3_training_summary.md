# NeXo v3.0 Master Training Summary

> **AUTHORITATIVE SOURCE: `notebooks/models/metrics.json`** (computed 2026-05-25 by
> `scripts/dump_model_metrics.py`, read from the `*_model_card.md` files). This file is a
> human-readable mirror of those honest numbers. If any figure here ever disagrees with
> `metrics.json`, **`metrics.json` wins** — regenerate this mirror, do not hand-edit it away.
>
> The pre-2026-05-25 version of this file carried superseded numbers (CEM R²=0.9933,
> VAE ROC-AUC=0.9307, RAT ROC-AUC=0.9605). Those predate the RAT leakage fix (notebook 04)
> and the final honest training run. They are gone. Never quote them.

## Datasets
| Model | Samples | Train Split | Test Split | Real % | Simulated % |
|-------|---------|-------------|-----------|--------|-------------|
| CEM   | 2,468,026 | 2,097,822 | 370,204 | 39.2% | 60.8% |
| VAE (Anomaly) | 499,729 | 424,769 | 74,960 | 60.0% | 40.0% |
| RAT   | 2,468,026 | 2,097,822 | 370,204 | 39.2% | 60.8% |

## Results (from metrics.json)
| Model | Algorithm | Features | Headline Metric | Value |
|-------|-----------|----------|-----------------|-------|
| CEM | LightGBM (DART) | 13 | Test R² | **0.9784** (MAE 0.0304, RMSE 0.0322) |
| VAE (Anomaly) | Variational Autoencoder (PyTorch) | 9 | ROC-AUC | **0.9821** (PR-AUC 0.9974) |
| RAT | XGBoost Classifier | 19 | ROC-AUC (temporal hold-out) | **0.9203** (F1 0.8927) |

### RAT — additional splits (leakage-controlled)
- Temporal hold-out: ROC-AUC 0.9203, F1 0.8927
- Random split: ROC-AUC 0.9419, F1 0.8418
- 5-fold stratified CV: ROC-AUC 0.9352, PR-AUC 0.8912

## Artifacts
- `cem_v3_lightgbm_gpu.joblib` (card: `cem_v3_model_card.md`)
- `oss_vae_v3_gpu.pt` (card: `oss_vae_v3_model_card.md`)
- `rat_v3_xgb_gpu.joblib` (card: `rat_underservice_v3_model_card.md`)

_Last synced to metrics.json: 2026-07-23._
