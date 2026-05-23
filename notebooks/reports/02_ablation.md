# Notebook 02 — Ablation Report

**Date:** 2026-05-22
**Cells before:** 20 → **after:** 22

## Applied

| ID | Change | Cell |
|---|---|---|
| E1 | Papermill `parameters`-tagged constants cell | new cell 2 |
| E2 | Title cell rewritten — CRISP-DM Phase 4 banner + input/output contract + pipeline diagram + "what this notebook does NOT do" | cell 0 |
| E3 | SEED + numpy + random + PYTHONHASHSEED (full notebook-level seeding) | new cell 2 |
| E4 | Every LightGBM hyperparameter named (LGB_NUM_LEAVES, LGB_MAX_DEPTH, etc.) — kills 10+ inline literals | new cell 2 |
| E5 | Artifact filenames named (MODEL_FNAME, FEATURES_FNAME, CARD_FNAME) — immutable contract | new cell 2 |

## Bugs fixed: 0 (logic untouched)
## Smells reduced: 2 (S1 — full SEED; S2 — parameters cell present)
## Gaps closed: 0 (G1-G8 deferred to next pass)
## Documentation added: explainer.md (extensive)

## Contracts preserved

- `models/cem_v3_lightgbm.joblib` — filename **unchanged** (services/ai-service/model_cache.py)
- `models/cem_v3_feature_names.joblib` — filename **unchanged**
- `models/cem_v3_model_card.md` — filename **unchanged**
- MinIO `curated/models/` mirror — **unchanged**

## Verification

1. Open notebook in Jupyter.
2. Run constants cell — must print all hyperparams with SEED=42.
3. Run full notebook — final cell saves to same paths as before.
4. `ls notebooks/models/` should show `cem_v3_lightgbm.joblib` etc. with new mtime.
5. POST `/models/reload` to ai-service → check log says `loaded CEM v3 model`.

## Deferred work (next pass)

- StratifiedKFold(5) wrapper around train (G1)
- Optuna 50-trial study with TPE sampler (G2)
- SHAP global beeswarm + per-area summary plot (G3)
- IsotonicRegression on predicted-vs-actual quantiles (G4)
- Quantile regression OR bootstrap for prediction intervals (G5)
