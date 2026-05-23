# Notebook Enhancement Reports

> Defense-grade audit + enhancement of all 6 NeXo notebooks (freeze: first week June 2026).
> Produced by the `nexo-notebook-enhancer` workflow. Each notebook gets three reports:
> **findings** (what's wrong), **ablation** (what changed), **explainer** (learn every concept from scratch).

## What this folder is for

If you don't understand a term in a notebook cell (skew, log1p, β-VAE, Granger F-test, `scale_pos_weight`…),
open that notebook's `NN_explainer.md` — it defines everything from zero, in plain language, with the
defense talking points called out.

## Index

| NB | Topic | CRISP-DM | Findings | Ablation | Explainer | Commit |
|----|-------|----------|----------|----------|-----------|--------|
| 00 | EDA — data understanding | Phase 2 | [00_findings](00_findings.md) | [00_ablation](00_ablation.md) | [00_explainer](00_explainer.md) | `fb5d9bf` |
| 01 | ETL + feature engineering | Phase 3 | [01_findings](01_findings.md) | [01_ablation](01_ablation.md) | [01_explainer](01_explainer.md) | `5d79359` |
| 02 | CEM score — LightGBM | Phase 4 | [02_findings](02_findings.md) | [02_ablation](02_ablation.md) | [02_explainer](02_explainer.md) | `707a6ab` |
| 03 | OSS anomaly — VAE | Phase 4 | [03_findings](03_findings.md) | [03_ablation](03_ablation.md) | [03_explainer](03_explainer.md) | `81d5935` |
| 04 | RAT underservice — XGBoost | Phase 4 | [04_findings](04_findings.md) | [04_ablation](04_ablation.md) | [04_explainer](04_explainer.md) | `7dfa44e` |
| 10 | Granger causality gate | Phase 4 | [10_findings](10_findings.md) | [10_ablation](10_ablation.md) | [10_explainer](10_explainer.md) | `618bcd8` |

## What was applied (every notebook)

1. **Papermill `parameters`-tagged constants cell** — `SEED=42` + full numpy/random(/torch) seeding + every magic number named. The `retrain-service` (papermill) can override these without editing code.
2. **Title rewrite** — CRISP-DM phase banner + explicit input/output contract + pipeline diagram + "what this notebook does NOT do".
3. **Constant wiring** — inline literals (thresholds, hyperparameters, split fractions, filenames) replaced with the named constants.
4. **Three reports** — findings / ablation / explainer.

## Findings totals

| NB | Bugs | Smells | Gaps | Total |
|----|------|--------|------|-------|
| 00 | 6 | 11 | 11 | 28 |
| 01 | 5 | 6 | 9 | 20 |
| 02 | 3 | 6 | 8 | 17 |
| 03 | 4 | 6 | 8 | 18 |
| 04 | 4 | 7 | 8 | 19 |
| 10 | 4 | 6 | 7 | 17 |
| **Σ** | **26** | **42** | **51** | **119** |

## Immutable contracts honored (NEVER renamed)

- `curated/warehouse.parquet` schema — consumed by pipeline-worker + ai-service.
- Joblib / PyTorch artifact filenames (`cem_v3_lightgbm.joblib`, `oss_vae_v3.pt`, `rat_underservice_v3_xgb.joblib`, + feature-name + scaler files) — consumed by `services/ai-service/model_cache.py` (mtime hot-reload).
- `granger_feature_gate.json` top-level keys — consumed by `services/api-gateway` `/granger-causality/lead-time`.
- `TT_data/` is CONFIDENTIAL — never read/exported; only schemas + aggregates appear in outputs.

## Deferred work (after defense freeze)

Each `NN_ablation.md` lists deep upgrades intentionally NOT applied this pass, because they change
model weights / gate numbers and need before/after measurement:

- **02/04:** Optuna HPO, SHAP global+per-segment, StratifiedKFold/GroupKFold, calibration, threshold sweep.
- **03:** KL annealing, β-sweep, early stopping, latent UMAP, persisted anomaly threshold.
- **10:** ADF/KPSS stationarity gate + differencing, BIC lag selection, Benjamini–Hochberg FDR, reverse-Granger, bootstrap CIs.

Rationale: enhancing structure + explainability now (zero artifact risk); applying metric-changing
rigor later, deliberately, with old-vs-new diffs.
