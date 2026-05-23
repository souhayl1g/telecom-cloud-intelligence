# Notebook 02 — Code Review Findings

**Notebook:** `notebooks/02_cem_score_training.ipynb`
**Date:** 2026-05-22

## BUGS

| # | Cell | Finding |
|---|---|---|
| B1 | 10 (LGB params) | Hyperparameters `num_leaves=256, max_depth=12, lr=0.05` etc. inline with no justification or ablation. No source citation. |
| B2 | 10 (early stop) | `stopping_rounds=30` magic number. Should be a constant with reasoning (`30 ≈ 5% of n_estimators=600`). |
| B3 | 18 (save) | Saves to `models/cem_v3_lightgbm.joblib` then mirrors to MinIO `curated/models/` — no `mtime` touch documented. ai-service relies on mtime to hot-reload. |

## SMELLS

| # | Finding |
|---|---|
| S1 | No top-of-file `SEED` constant (only `random_state=42` inside params dict — incomplete) |
| S2 | No papermill `parameters` cell — retrain container can't override hyperparameters |
| S3 | No CV — single train/val/test split. R²=0.9933 is on ONE random partition, not CV-averaged |
| S4 | No SHAP — `model.feature_importances_` shown but tree-importance is biased toward high-cardinality features |
| S5 | No threshold sweep / PR curve for the binarized "low-CEM-subscriber" intervention trigger |
| S6 | No comparison vs GBR baseline (model card claims LightGBM wins — but baseline isn't trained in this notebook) |

## GAPS

| # | Finding |
|---|---|
| G1 | StratifiedKFold(5) cross-validation missing |
| G2 | Optuna 50-trial study missing (model claims "tuned" but tuning logic isn't visible) |
| G3 | SHAP global + per-area analysis missing |
| G4 | Isotonic calibration on predicted score → empirical-quantile mapping missing |
| G5 | Prediction interval / confidence bounds missing |
| G6 | No "what this shows / what to look for" markdown narrative |
| G7 | No Limitations cell |
| G8 | Model card auto-generation hardcoded — should pull metrics from a `summary` dict |

## Counts

- BUGS: 3
- SMELLS: 6
- GAPS: 8
- TOTAL: 17

## Applied in this pass

- E1: Constants cell (papermill `parameters`-tagged) with full SEED setup + every hyperparameter named
- E2: Title rewritten with CRISP-DM Phase 4 banner + explicit input/output contract + pipeline diagram + "does NOT do" section

## Deferred (documented in explainer)

- Optuna HPO (G2)
- SHAP analysis (G3, S4)
- StratifiedKFold (G1, S3)
- Isotonic calibration (G4)
- Prediction intervals (G5)
- GBR baseline comparison (S6)

Rationale: half-implementing changes the joblib artifact contract that `services/ai-service/model_cache.py` reads via mtime. Apply in dedicated follow-up pass.
