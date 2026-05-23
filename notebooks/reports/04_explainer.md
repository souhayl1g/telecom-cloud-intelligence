# Notebook 04 — Plain-Language Explainer (RAT Underservice · XGBoost)

> Audience: you (Souhayl) — every term defined from scratch.
> What this notebook does: **predicts which subscribers are "underserved" — 4G-capable but stuck on slow 2G/3G.**
> This is **CRISP-DM Phase 4 — Modeling** (supervised classification branch).

---

## The Big Picture

Some subscribers own a 4G-capable SIM/device but their traffic still rides mostly 2G/3G — a bad experience and a churn risk. We call that **underservice**. We want a model that, given a subscriber's features, outputs the **probability** they're underserved. High-probability subscribers feed the `pb-churn-prevention` playbook (SMS + tickets).

Unlike nb 03 (no labels → unsupervised VAE), here we DO have a signal: the `rat_gap_score` feature from nb 01. We turn it into a yes/no label and train a **supervised classifier**.

---

## Concepts Used

### 1. Binary Classification

Predict one of two classes: underserved (1) or not (0). The model outputs a **probability** ∈ [0,1]; we threshold it to get the class. Contrast with regression (nb 02 predicts a continuous number).

### 2. Making the Label (`RAT_LABEL_THRESHOLD = 0.30`)

```python
y = (subs['rat_gap_score'] > RAT_LABEL_THRESHOLD).astype(int)
```

`rat_gap_score` is a continuous 0–1 feature (how big the gap between capability and actual RAT usage is). We **binarize** it: above 0.30 → underserved (1), else 0. This threshold DEFINES the positive class, so it's a load-bearing number — now a named constant, not buried inline. A sensitivity check (does 0.25 vs 0.35 change the model's usefulness?) is deferred (`04_findings.md`).

> Note: `rat_gap_score` is dropped from the FEATURES (see the `DROP` set) — otherwise the model would just read the answer off its own input (target leakage).

### 3. XGBoost (the algorithm)

**XGBoost** = eXtreme Gradient Boosting. Same boosting idea as LightGBM (nb 02): sequential trees, each correcting the previous ensemble's errors. Differences vs LightGBM:
- Grows trees **level-wise** (balanced) by default, with strong built-in regularization.
- The tabular gold-standard — wins most Kaggle structured-data competitions.

Key params here:
- `XGB_N_ESTIMATORS=500` — max boosting rounds.
- `XGB_MAX_DEPTH=8` — tree depth; controls how many features can interact in one path.
- `XGB_LEARNING_RATE=0.07` — shrinkage per round (small = robust).
- `XGB_TREE_METHOD='hist'` — histogram split-finding (fast, GPU-friendly).
- `objective='binary:logistic'` — outputs a probability via the logistic (sigmoid) function.
- `eval_metric='auc'` — watches ROC-AUC on the validation set during training.

### 4. GPU with CPU Fallback

```python
model.set_params(device='cuda'); model.fit(...)   # try GPU
except: model = xgb.XGBClassifier(**params); model.fit(...)  # CPU fallback
```

XGBoost can train on the RTX 3050 GPU (`device='cuda'` + `tree_method='hist'`). If CUDA isn't available it falls back to CPU. (Smell S7: the fallback refits from scratch — minor wasted work — noted for cleanup.)

### 5. Class Imbalance + `scale_pos_weight`

Underserved subscribers are the MINORITY. If 10% are positive, a lazy model can score 90% accuracy by always predicting "not underserved" — useless. **`scale_pos_weight`** tells XGBoost to weight positive-class errors more heavily:

```
scale_pos_weight = (# negatives) / (# positives)
```

So if negatives outnumber positives 9:1, each positive counts ~9×. This rebalances the gradient so the model actually learns the rare class. (The code computes `spw = neg/pos`.)

### 6. Why `accuracy` is the wrong metric here — use ROC-AUC + F1

- **ROC-AUC** — probability the model ranks a random positive above a random negative. Threshold-free, robust to imbalance. We report this on both splits.
- **F1** — harmonic mean of precision and recall at a chosen threshold (`DECISION_THRESHOLD=0.50`). Balances "of those we flagged, how many were right" (precision) against "of the truly underserved, how many did we catch" (recall).

> The 0.50 cutoff is arbitrary for an imbalanced problem. A **threshold sweep** (plot precision & recall vs threshold, pick the point matching your SMS/ticket budget) is the proper approach — deferred (G2).

### 7. Two Evaluation Regimes

The notebook scores the model TWICE:

- **Random split** (`splits['random']`) — train/val/test drawn randomly. Best-case number.
- **Temporal hold-out** (`splits['temporal']['holdout_indices']`) — the LAST month reserved entirely. Tests whether the model survives **drift** (subscriber behavior shifting month to month). This is the production-realistic number.

For defense, reporting BOTH is honest and impressive: "0.96 random, 0.9X temporal — the model holds up on future data."

### 8. Feature Importance vs SHAP

`model.feature_importances_` (gain) ranks features by how much they reduced loss across splits. Same caveat as nb 02: **biased toward high-cardinality continuous features**. SHAP would give fair, additive, per-subscriber attributions and could be sliced per-RAT or per-area — deferred (G3).

### 9. The Deferred Best-Practices (and why they matter)

- **GroupKFold by area** — random splitting can put the same governorate in both train and test, so the model "memorizes" geography → inflated metric. GroupKFold guarantees each area sits entirely in one fold. The honest spatial-generalization metric (G1).
- **Monotonic constraints** — physically, more 2G traffic share should never DECREASE underservice probability. XGBoost can enforce monotonic relationships per feature (`monotone_constraints`), making the model both more accurate AND more defensible (G4).
- **Probability calibration** — `binary:logistic` scores rank well but aren't guaranteed to be true probabilities (a "0.7" may not mean 70% chance). Isotonic/Platt calibration fixes this so the score is trustworthy for budgeting interventions (G6).
- **`fillna(0)` fix** — filling missing KPIs with 0 conflates "missing" with "genuinely zero." Better: median impute + a `was_missing` indicator column (B4, G8).

These are documented, not implemented this pass, because each changes the saved joblib model that `ai-service` hot-reloads — they belong in a measured follow-up.

---

## The papermill `parameters` Cell

`retrain-service` (port 8004) runs this notebook via **papermill**, which can override the `parameters`-tagged cell. So `RAT_LABEL_THRESHOLD`, all XGB hyperparameters, `DECISION_THRESHOLD`, and artifact filenames are named constants there — ops can retrain with a stricter label or different threshold without touching code.

---

## The Artifact Contract (do not rename)

| File | Consumed by |
|---|---|
| `models/rat_underservice_v3_xgb.joblib` | `services/ai-service/model_cache.py` (mtime hot-reload) |
| `models/rat_v3_feature_names.joblib` | ai-service — exact feature column order at inference |
| `models/rat_underservice_v3_model_card.md` | docs / defense evidence |

Mirrored to MinIO `curated/models/`. ai-service watches file **mtime** — re-saving triggers an auto-reload on the next inference call.

---

## Glossary

| Term | Definition |
|---|---|
| Binary classification | Predict one of two classes (here: underserved yes/no) |
| Label / target | The 0/1 answer the model learns to predict |
| Binarize | Turn a continuous score into 0/1 via a threshold |
| Target leakage | Letting the answer sneak into the features → fake-high score |
| XGBoost | Extreme gradient boosting — tabular gold-standard |
| n_estimators / max_depth / learning_rate | Max trees / tree depth / per-tree shrinkage |
| tree_method='hist' | Histogram split-finding (fast, GPU-capable) |
| binary:logistic | Objective that outputs a probability via sigmoid |
| scale_pos_weight | neg/pos ratio; up-weights the rare positive class |
| ROC-AUC | Threshold-free ranking quality (1 = perfect) |
| F1 | Harmonic mean of precision & recall at a threshold |
| Decision threshold | Probability cutoff turning a score into a class |
| Random vs temporal split | Best-case vs drift-realistic evaluation |
| GroupKFold | CV keeping each group (area) entirely in one fold |
| Monotonic constraint | Force a feature's effect to only ever increase/decrease |
| Calibration | Make output scores behave like true probabilities |
| SHAP | Fair, additive per-prediction feature attribution |

---

## Quick Read

1. **Cell 0:** title + CRISP-DM Phase 4 banner + contract + dual-eval note.
2. **Cell 3 (new):** all constants + SEED + seeding. Papermill-overridable.
3. **Load:** read `subscribers.parquet` + `splits.json`.
4. **Label + features:** binarize `rat_gap_score > RAT_LABEL_THRESHOLD`; drop leak columns; select numeric features.
5. **Split + class weight:** apply random split; compute `scale_pos_weight = neg/pos`.
6. **Train:** XGBoost on GPU (CPU fallback), early-watch val AUC.
7. **Evaluate (random):** ROC-AUC + F1 at `DECISION_THRESHOLD`.
8. **Evaluate (temporal):** same metrics on the held-out last month.
9. **Importance:** top-`TOP_K_IMPORTANCE` features (SHAP deferred).
10. **Save:** joblib model + feature names + model card → local + MinIO.
