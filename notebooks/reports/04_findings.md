# Notebook 04 — Code Review Findings

**Notebook:** `notebooks/04_rat_underservice_training.ipynb`
**Date:** 2026-05-23

## BUGS

| # | Cell | Finding |
|---|---|---|
| B1 | label | `rat_gap_score > 0.3` label threshold inline — defines the entire positive class, no provenance, no sensitivity check. |
| B2 | params | `n_estimators=500, max_depth=8, learning_rate=0.07` inline literals, no constants, citing only a doc comment. |
| B3 | eval | `(pte>0.5)` decision threshold hardcoded for F1 — 0.5 is arbitrary for an imbalanced problem; should be tuned. |
| B4 | features | `X = subs[feat_cols].fillna(0)` — fills NaN with 0 silently. For some KPIs 0 is a meaningful value, not "missing" → distorts splits. |

## SMELLS

| # | Finding |
|---|---|
| S1 | No global `SEED` (only `random_state=42` inside params) — numpy/python `random` unseeded. |
| S2 | No papermill `parameters` cell — retrain container can't override threshold/hyperparams. |
| S3 | `scale_pos_weight=spw` computed but the formula (`neg/pos`) not annotated — reader can't tell why. |
| S4 | F1@0.5 reported but no PR curve / threshold sweep — operating point not justified. |
| S5 | `feature_importances_` (gain) shown — biased toward high-cardinality features; no SHAP. |
| S6 | No GroupKFold by cell-site/area — random split lets the same geography sit in train AND test (spatial leakage). |
| S7 | GPU try/except refits from scratch on failure — silently doubles work and discards the half-trained model. |

## GAPS (best-of-best missing)

| # | Finding |
|---|---|
| G1 | No **GroupKFold** by area — geographic leakage inflates the random-split metric. |
| G2 | No **threshold sweep** — should plot precision/recall vs threshold and pick the operating point that matches the intervention budget. |
| G3 | No **SHAP** global + per-segment (RAT, area) — tree importance is biased. |
| G4 | No **monotonic constraints** — physically, higher `traffic_2g_share` should never DECREASE underservice probability; XGBoost can enforce this. |
| G5 | No **scale_pos_weight ablation** / `Optuna` tuning — class-weight chosen by formula only. |
| G6 | No **calibration** (Platt/isotonic) — `binary:logistic` outputs are not guaranteed calibrated probabilities. |
| G7 | No "Limitations" markdown cell. |
| G8 | `fillna(0)` masks missingness — should use a sentinel + missing-indicator column or median impute. |

## Counts

- BUGS: 4
- SMELLS: 7
- GAPS: 8
- TOTAL: 19

## Applied in this pass

- E1: Papermill `parameters`-tagged constants cell — SEED + numpy/random seeding + `RAT_LABEL_THRESHOLD`, all XGB hyperparams, `DECISION_THRESHOLD`, `TOP_K_IMPORTANCE`, immutable artifact filenames.
- E2: Title rewritten — CRISP-DM Phase 4 banner + I/O contract + pipeline diagram + dual-eval explanation + "does NOT do".
- E3: Wired constants into label / params / both eval cells / importance / save — killed 8 inline literals.

## Deferred (documented in explainer)

- GroupKFold (G1), threshold sweep (G2), SHAP (G3), monotonic constraints (G4), calibration (G6) — change metrics/artifact; apply in a dedicated pass with before/after logged.
- `fillna(0)` → median + missing-indicator (B4, G8) — coordinate with nb 01 imputer to avoid double-imputation.

Rationale: re-tuning threshold or adding monotonic constraints changes the joblib model that ai-service hot-reloads. Explainer documents WHAT + WHY + HOW; apply after defense freeze.
