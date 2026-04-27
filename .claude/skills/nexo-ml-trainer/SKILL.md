---
name: nexo-ml-trainer
description: Train and evaluate AI v3.0 models for Telecom NeXoligence. Use when: (1) training CEM Score (LightGBM), (2) training Experience Anomaly (VAE), (3) training RAT Underservice (CatBoost), (4) training Churn Trajectory (TFT), (5) evaluating models with real metrics, (6) saving model artifacts for ai-service inference endpoints.
---

# NeXo ML Trainer

Train 4 production ML models on real + simulated TT BSS data.

## Model Inventory

| Model | Algorithm | Input | Output | Notebook |
|---|---|---|---|---|
| CEM Score | LightGBM + SHAP | 10 BSS+OSS features | score 0-1 + explanation | `notebooks/v3/04_cem_score_lgbm.ipynb` |
| Experience Anomaly | VAE (PyTorch) | 26 CEM features | anomaly_score + latent | `notebooks/v3/05_experience_anomaly_vae.ipynb` |
| RAT Underservice | CatBoost | generation × highest_rat × area | underservice_risk | `notebooks/v3/06_rat_underservice_catboost.ipynb` |
| Churn Trajectory | TFT (pytorch-forecasting) | 5-month sequences | churn_prob 30/60/90d | `notebooks/v3/07_churn_trajectory_tft.ipynb` |

## Training Workflow

### 1. Data Split

Use time-based split (never random):
- **Train**: Feb (468K real) + Mar (500K real) + Jan (500K simulated)
- **Val**: Apr (500K simulated)
- **Test**: May (500K simulated)

### 2. CEM Score (LightGBM)

```python
import lightgbm as lgb
import shap

X_train, y_train = ...  # from subscriber_features + area aggregates
model = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=63)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(50)])

# SHAP explanation
explainer = shap.TreeExplainer(model)
shap_values = explainer(X_val)
shap.plots.beeswarm(shap_values)

joblib.dump(model, "notebooks/models/v3/cem_score_lgbm.joblib")
```

### 3. Experience Anomaly (VAE)

```python
class VAE(nn.Module):
    def __init__(self, input_dim=26, latent_dim=8):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Linear(32, latent_dim * 2))
        self.decoder = nn.Sequential(nn.Linear(latent_dim, 32), nn.ReLU(), nn.Linear(32, input_dim))

# Train on normal subscribers only (95%)
# Anomaly threshold = p95 reconstruction error
torch.save(vae.state_dict(), "notebooks/models/v3/exp_anomaly_vae.pt")
```

### 4. RAT Underservice (CatBoost)

```python
from catboost import CatBoostClassifier
cat_features = ["generation", "highest_rat", "area"]
model = CatBoostClassifier(iterations=500, depth=6, cat_features=cat_features)
model.fit(X_train, y_train, eval_set=(X_val, y_val), early_stopping_rounds=50)
model.save_model("notebooks/models/v3/rat_underservice_catboost.cbm")
```

### 5. Churn Trajectory (TFT)

```python
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
# Build sequences: per-imsi, 5-month rolling window
# Static: area, generation
# Time-varying: cem_score, rat_gap_score, network_experience_index, data_intensity
# Target: churn_risk_flag (next month)
training = TimeSeriesDataSet(df, time_idx="time_idx", target="churn_risk_flag",
                              group_ids=["imsi_hash"],
                              static_categoricals=["area", "generation"],
                              time_varying_unknown_reals=["cem_score", "rat_gap_score"])
tft = TemporalFusionTransformer.from_dataset(training, learning_rate=0.03, hidden_size=32)
trainer.fit(tft, train_dataloaders=train_dl, val_dataloaders=val_dl)
trainer.save_checkpoint("notebooks/models/v3/churn_tft.ckpt")
```

## Evaluation Targets

| Model | Metric | Target |
|---|---|---|
| CEM Score | R² | > 0.90 |
| RAT Underservice | F1 | > 0.85 |
| Experience Anomaly | ROC-AUC | > 0.90 |
| Churn Trajectory | AUC | > 0.85 |

## Inference Integration

After training, add router to `services/ai-service/routers/v3/`:
- `POST /infer/cem-score` — LightGBM + SHAP
- `POST /infer/exp-anomaly` — VAE reconstruction error
- `POST /infer/rat-underservice` — CatBoost
- `POST /infer/churn-trajectory` — TFT multi-horizon

## Key Files

- `notebooks/v3/` — Training notebooks
- `services/ai-service/routers/v3/` — Inference endpoints
- `services/ai-service/model_cache.py` — Model loader
