# Notebook 02 — Plain-Language Explainer (CEM Score · LightGBM)

> Audience: you (Souhayl) — every term defined from scratch.
> What this notebook does: **learns to predict the CEM experience score (0–1) for any subscriber from their features.**
> This is **CRISP-DM Phase 4 — Modeling.**

---

## The Big Picture

Notebook 01 produced `warehouse.parquet` with a **target column** `cem_score` (computed by formula) plus ~30 feature columns. Notebook 02 trains a model so that — given a NEW subscriber where we did NOT pre-compute the formula — the model predicts their CEM score from features alone.

Why learn a formula we already have? Two reasons:
1. **Speed + generalization** — at inference the model needs only raw features, not the full OSS join.
2. **Feature attribution** — the trained model tells us WHICH features drive experience (via SHAP), which the hard-coded formula cannot.

---

## Concepts Used

### 1. Supervised Regression

**Regression** = predict a continuous number (here `cem_score ∈ [0,1]`), as opposed to **classification** (predict a category). "Supervised" = we show the model many `(features → known answer)` pairs and it learns the mapping.

### 2. Gradient Boosting (the core algorithm)

A **decision tree** asks yes/no questions (`traffic_4g_share > 0.6?`) and routes each row to a leaf holding a predicted value. One tree is weak.

**Gradient boosting** builds trees **sequentially**. Tree 1 predicts; we measure its errors (**residuals**). Tree 2 is trained to predict those residuals — i.e. to fix tree 1's mistakes. Tree 3 fixes what's left, and so on. Final prediction = sum of all trees' contributions, each scaled by the learning rate.

"Gradient" = each new tree follows the negative gradient of the loss function (steepest-descent on the error surface). For squared-error loss, the gradient IS the residual — which is why boosting "fits the residuals."

### 3. LightGBM specifically

**LightGBM** (Microsoft) is a fast gradient-boosting library. Two design choices matter:

- **Histogram binning** — continuous features are bucketed into ~255 bins, so split-finding scans bins not raw values. Big speedup on millions of rows (we have 2.47M).
- **Leaf-wise growth** — most libraries grow a tree level-by-level (balanced). LightGBM grows the **single leaf** with the largest loss reduction next. Result: deeper, asymmetric trees that fit faster — but can overfit, which is why `num_leaves` must be capped.

### 4. DART vs GBDT (`LGB_BOOSTING_TYPE`)

- **GBDT** = standard gradient boosting (every tree kept).
- **DART** (Dropouts meet Multiple Additive Regression Trees) = randomly **drops** a subset of already-built trees when computing the next tree's target. Like dropout in neural nets — prevents the first few trees from dominating ("over-specialization"). Slower but often higher accuracy. We use `dart` because the model card claims top-tier R².

### 5. `num_leaves` vs `max_depth` (`LGB_NUM_LEAVES=256`, `LGB_MAX_DEPTH=12`)

- `max_depth` = longest root-to-leaf path. Caps tree height.
- `num_leaves` = total leaves allowed. This is LightGBM's PRIMARY complexity knob (because growth is leaf-wise, not depth-wise).

Rule of thumb: `num_leaves ≤ 2^max_depth`. Here `2^12 = 4096`, and `256 ≪ 4096`, so depth is the binding constraint and the tree stays well-regularized. Higher `num_leaves` = more capacity = more overfit risk.

### 6. `learning_rate` (`LGB_LEARNING_RATE=0.05`)

Each tree's contribution is multiplied by this **shrinkage** factor before adding. Small rate (0.05) = each tree nudges gently → needs more trees but generalizes better. Large rate (0.3) = fast but jumpy, overfits. Classic trade-off: low `learning_rate` + high `n_estimators` + early stopping = the standard recipe.

### 7. `n_estimators` + Early Stopping (`LGB_N_ESTIMATORS=600`, `EARLY_STOP_ROUNDS=30`)

`n_estimators` = MAX trees. **Early stopping** watches the validation metric: if it doesn't improve for `EARLY_STOP_ROUNDS=30` consecutive trees, training halts and the best iteration is kept. So 600 is a ceiling, not a fixed count — the model self-selects how many trees it actually needs. `30 ≈ 5%` of 600 — a common patience setting.

### 8. Regularization (`LGB_REG_ALPHA=0.05`, `LGB_REG_LAMBDA=0.05`, `LGB_MIN_CHILD_SAMPLES=20`)

- `reg_alpha` = L1 penalty (pushes some leaf weights to exactly 0 → sparsity).
- `reg_lambda` = L2 penalty (shrinks all leaf weights smoothly).
- `min_child_samples=20` = a leaf must contain ≥20 rows, else the split is rejected. Stops the tree from carving out tiny noise-fitting leaves.

All three fight overfitting from different angles.

### 9. The Metrics: R², MAE, RMSE, MSE

After training we score on the held-out **test** set:

| Metric | Formula (intuition) | Reads as |
|---|---|---|
| **MAE** | mean(\|pred − actual\|) | average error in score units. MAE=0.013 → off by ~1.3% of the 0–1 range. |
| **MSE** | mean((pred − actual)²) | squared error; punishes big misses harder |
| **RMSE** | √MSE | same units as target; comparable to MAE but outlier-sensitive |
| **R²** | 1 − SS_res/SS_tot | fraction of variance explained. R²=0.9933 → model explains 99.33% of CEM-score variance. R²=0 → no better than predicting the mean. |

Why both MAE and RMSE? If RMSE ≫ MAE, a few large errors dominate (heavy-tailed residuals). If they're close, errors are uniform.

### 10. The Train/Val/Test Split (inherited from nb 01)

- **Train** — model learns here.
- **Val** — early stopping watches this; never trained on.
- **Test** — touched ONCE at the end for the honest metric. If you tune against test, the metric is no longer honest (leakage).

### 11. Feature Importance vs SHAP

`model.feature_importances_` counts how often / how much each feature is used in splits. **Problem:** it is **biased toward high-cardinality features** (continuous columns get more split opportunities than binary flags), so it can mislead.

**SHAP** (SHapley Additive exPlanations, Lundberg & Lee 2017) borrows from game theory: it fairly distributes each prediction among its features by asking "how much did feature X change this specific prediction vs its average?" SHAP values are **additive** (they sum to the prediction) and **consistent** (if a feature matters more, its SHAP value can't go down). A SHAP beeswarm plot shows, per feature, the spread + direction of impact across all subscribers — far more trustworthy than raw tree importance.

> Status in this notebook: SHAP is **documented here but not yet wired in** — see `02_findings.md` G3. Adding it does not change the saved model, only adds an analysis cell.

### 12. Cross-Validation (StratifiedKFold)

A single train/test split gives ONE number that depends on which rows landed in test. **K-fold CV** splits data into K parts, trains K times (each part is test once), and averages. **StratifiedKFold** keeps the target distribution balanced across folds (important when the target is skewed). CV-averaged R² is a more honest estimate than single-split R².

> Status: documented, deferred (G1) — adds a CV wrapper, doesn't alter the production artifact.

### 13. Hyperparameter Tuning with Optuna

The hyperparameters above (256 leaves, depth 12, lr 0.05…) were chosen by convention. **Optuna** automates the search: you define a `search space` and an `objective_fn` that trains a model and returns its validation score; Optuna's **TPE sampler** (Tree-structured Parzen Estimator) proposes the next set of hyperparameters by modeling which regions of the space gave good scores. After ~50 trials it returns the best config. Sketch:

```python
import optuna

def objective_fn(trial):
    params = {
        "num_leaves":    trial.suggest_int("num_leaves", 31, 512),
        "max_depth":     trial.suggest_int("max_depth", 4, 16),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
    }
    model = lgb.LGBMRegressor(**params, n_estimators=600)
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)],
              callbacks=[lgb.early_stopping(30)])
    return mean_absolute_error(y_val, model.predict(X_val))   # Optuna minimizes this

study = optuna.create_study(direction="minimize")
study.optimize(objective_fn, n_trials=50)
best = study.best_params
```

> Status: documented, deferred (G2). When added, the winning params replace the constants in the parameters cell.

### 14. Isotonic Calibration

A model can be **accurate on average but mis-scaled** in places — e.g. it systematically predicts 0.7 for subscribers whose true score is 0.6. **Isotonic regression** fits a monotonic (non-decreasing) step function mapping predicted → empirically-correct values, fixing such bias without reordering. Useful if the CEM score feeds a threshold-based intervention trigger.

> Status: documented, deferred (G4).

### 15. Temporal Holdout

Random split can leak time patterns. **Temporal holdout** = reserve the LAST month entirely as test. If test-on-future R² stays high, the model survives **drift** (data shifting month to month). For the defense, report both random-split (best case) and temporal-holdout (production-realistic) numbers.

---

## The papermill `parameters` Cell (why it exists)

The retrain container (`retrain-service`, port 8004) runs this notebook unattended via **papermill**. Papermill can OVERRIDE any variable in the cell tagged `parameters` — so ops can retrain with, say, `LGB_LEARNING_RATE=0.03` without editing the notebook. That is why every hyperparameter lives in that one cell as a named constant, not inline in the `.fit()` call.

---

## What This Notebook Does NOT Do

- Does not compute the CEM formula (that's nb 01).
- Does not touch OSS anomaly detection (nb 03) or RAT underservice (nb 04).
- Does not deploy — it only writes the joblib artifact that `ai-service` later hot-loads.

---

## The Artifact Contract (do not rename)

| File | Consumed by |
|---|---|
| `models/cem_v3_lightgbm.joblib` | `services/ai-service/model_cache.py` (mtime hot-reload) |
| `models/cem_v3_feature_names.joblib` | ai-service — column order at inference |
| `models/cem_v3_model_card.md` | docs / defense evidence |

Mirrored to MinIO `curated/models/`. The ai-service watches file **mtime**; re-saving with a new timestamp triggers an automatic reload on the next inference call — no restart needed.

---

## Glossary

| Term | Definition |
|---|---|
| Regression | Predict a continuous number |
| Gradient boosting | Sequential trees, each fixing the previous ensemble's errors |
| Residual | Actual − predicted; what the next tree targets |
| LightGBM | Fast histogram-based, leaf-wise boosting library |
| GBDT | Standard gradient-boosted decision trees |
| DART | Boosting with tree dropout — anti over-specialization |
| Leaf-wise growth | Grow the highest-loss leaf next (vs level-wise) |
| num_leaves | Max leaves per tree — LightGBM's main complexity knob |
| learning_rate | Per-tree shrinkage; small = slow + robust |
| Early stopping | Halt when validation stops improving |
| reg_alpha / reg_lambda | L1 / L2 weight penalties |
| R² | Fraction of variance explained (1 = perfect) |
| MAE / RMSE | Mean absolute / root-mean-squared error |
| SHAP | Game-theoretic, fair per-feature attribution |
| StratifiedKFold | K-fold CV preserving target balance |
| Optuna / TPE | Automated hyperparameter search |
| Isotonic calibration | Monotonic remap of predictions to fix scale bias |
| Temporal holdout | Reserve last month as test to detect drift |
| papermill | Runs a notebook with overridable parameters |

---

## Quick Read

1. **Cell 0:** title + CRISP-DM Phase 4 banner + contract.
2. **Cell 2 (new):** all hyperparameters as named constants + `SEED=42`. Papermill-overridable.
3. **Load:** read `warehouse.parquet` + train/val/test splits.
4. **Train:** `LGBMRegressor(**params)` with early stopping on val.
5. **Evaluate:** R² / MAE / RMSE on test.
6. **Importance:** top-K feature importances (SHAP deferred — see findings G3).
7. **Save:** joblib model + feature names + model card → local `models/` + MinIO mirror.
