# Notebook 04 — Ablation Report

**Date:** 2026-05-23
**Cells before:** 18 → **after:** 19

## Applied

| ID | Change | Cell |
|---|---|---|
| E1 | Papermill `parameters`-tagged constants cell (SEED + seeding + label threshold + all XGB params + decision threshold + top-K + artifact fnames) | new cell 3 |
| E2 | Title rewritten — CRISP-DM Phase 4 banner + I/O contract + pipeline diagram + dual-eval explanation + "does NOT do" | cell 0 |
| E3 | Label: `> 0.3` → `> RAT_LABEL_THRESHOLD` | label cell |
| E4 | Params dict: every literal → constant; `random_state=42` → `SEED` | train cell |
| E5 | F1 decision threshold `0.5` → `DECISION_THRESHOLD` in BOTH random + temporal eval cells | eval cells |
| E6 | Importance `.head(20)` → `.head(TOP_K_IMPORTANCE)` | importance cell |
| E7 | Save: 3 artifact filenames → constants | save cell |

## Bugs fixed: 0 (model logic untouched — identical fit given same seed)
## Smells reduced: 2 (S1 — full SEED; S2 — parameters cell present)
## Gaps closed: 0 (G1–G8 deferred — see findings.md)
## Documentation added: explainer.md (extensive)

## Contracts preserved

- `models/rat_underservice_v3_xgb.joblib` — filename **unchanged** (`services/ai-service/model_cache.py`)
- `models/rat_v3_feature_names.joblib` — **unchanged**
- `models/rat_underservice_v3_model_card.md` — **unchanged**
- MinIO `curated/models/` mirror — **unchanged**
- Feature column order (`feat_cols`) — **unchanged** (same DROP set, same dtype filter)

## Verification

1. Open notebook in Jupyter.
2. Run constants cell — prints `SEED=42 | label>0.3 | xgb=500t/depth8/lr0.07 | thr=0.5`, no error.
3. Run full notebook — final cell saves `.joblib` to same path; model card shows random + temporal metrics.
4. `POST /models/reload` to ai-service → RAT model reloaded (mtime changed).
5. `POST /infer/rat-underservice` with a sample subscriber → returns underservice probability.

## Deferred work (next pass)

- GroupKFold by area — remove spatial leakage from the random-split metric.
- Threshold sweep — plot P/R vs threshold, pick operating point by intervention budget.
- SHAP global + per-RAT/area — replace biased gain importance.
- Monotonic constraints — enforce `traffic_2g_share ↑ ⇒ underservice ↑`.
- Probability calibration (isotonic) so outputs are usable as real probabilities.
- Replace `fillna(0)` with median impute + missing-indicator (coordinate with nb 01).
