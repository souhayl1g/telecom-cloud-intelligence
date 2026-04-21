---
name: mlops-python
description: "MLOps patterns for scikit-learn, PyTorch, and production ML pipelines. Actions: train, evaluate, improve, debug, optimize, retrain, explain, implement, add model, review ML code. Elements: model training, feature engineering, anomaly detection, classification, regression, autoencoder, LSTM, GRU, IsolationForest, GradientBoosting, XGBoost, joblib serialization, model reload, inference endpoint, rolling window, pipeline step. Topics: CEM experience scoring, churn prediction, anomaly detection, RAT underservice, Granger causality."
---
# MLOps Patterns — Telecom AI Platform

## Current Model Stack (v2.0 — scikit-learn)
| Model | File | Algorithm | Input | Output |
|-------|------|-----------|-------|--------|
| SLA Risk | `sla_risk_model.joblib` | GradientBoostingRegressor (200 est, depth=4) | 6 KPI features | risk score 0-1 |
| OSS Anomaly | `anomaly_model.joblib` | IsolationForest (150 est, contamination=0.05) | OSS KPIs | -1/1 label |
| BSS Anomaly | `revenue_anomaly_model.joblib` | IsolationForest (150 est, contamination=0.05) | BSS features | -1/1 label |

## Planned Stack (v3.0 — real TT data)
| Model | Algorithm | Blocks on |
|-------|-----------|-----------|
| CEM Experience Score | GradientBoostingRegressor (interpretable) | BSS data ✅ + OSS ⏳ |
| Experience Anomaly | Autoencoder (PyTorch) | OSS data ⏳ |
| Churn Trajectory | LSTM/GRU (PyTorch) | Accumulated window history |
| RAT Underservice | XGBoost / small NN | OSS + BSS joined |
| O+B Correlation | Granger Causality | OSS data ⏳ |

## Scikit-learn Patterns

### Training
```python
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest
from sklearn.model_selection import cross_val_score
import joblib

model = GradientBoostingRegressor(n_estimators=200, max_depth=4, random_state=42)
model.fit(X_train, y_train)
scores = cross_val_score(model, X, y, cv=5, scoring='r2')
joblib.dump(model, 'models/model_name.joblib')
```

### Inference Endpoint (FastAPI)
```python
model = joblib.load("models/model.joblib")

@app.post("/infer/endpoint")
async def infer(data: ModelInput):
    features = np.array([[data.feature1, data.feature2, ...]])
    prediction = model.predict(features)[0]
    return {"score": float(prediction)}

@app.post("/models/reload")
async def reload_models():
    global model
    model = joblib.load("models/model.joblib")
    return {"status": "reloaded"}
```

## PyTorch Autoencoder (planned — Experience Anomaly)
```python
class ExperienceAutoencoder(nn.Module):
    def __init__(self, input_dim=26, latent_dim=8):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16), nn.ReLU(),
            nn.Linear(16, latent_dim)
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 16), nn.ReLU(),
            nn.Linear(16, input_dim)
        )
    def forward(self, x):
        return self.decoder(self.encoder(x))
    def reconstruction_error(self, x):
        return F.mse_loss(self.forward(x), x, reduction='none').mean(dim=1)
```
Anomaly threshold: `mean(errors) + 2*std(errors)` on validation set.

## PyTorch LSTM (planned — Churn Trajectory)
```python
class ChurnLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()
    def forward(self, x):  # x: (batch, seq_len, features)
        out, _ = self.lstm(x)
        return self.sigmoid(self.fc(out[:, -1, :]))
```
Input: rolling window sequences from the window engine (last W cycles per subscriber).

## Rolling Window Engine (planned)
```python
# Per 2-min pipeline cycle:
# 1. Sample batch from 500K BSS CSV (stratified by area/usertype/rat)
# 2. Compute derived features (delta, rolling mean/std over last W cycles)
# 3. Append to window buffer in PostgreSQL or MinIO
# 4. Feed to models: latest snapshot → CEM score, AE anomaly; sequences → LSTM churn
```

## Feature Engineering — Real BSS Data (26 features)
Key CEM features: `data_usage_mb`, `voice_minutes`, `sms_count`, `avg_session_duration`,
`rat_type` (2G/3G/4G/5G), `device_category`, `data_plan_type`, `area_code`,
`complaint_count`, `service_disruptions`, `qoe_score` (computed).

Derived features to compute:
- `usage_trend` = current - 30d_avg
- `disruption_rate` = disruptions / days_active
- `rat_capability_gap` = device_max_rat - actual_rat (→ RAT underservice signal)
- `experience_score` = weighted composite of QoE indicators (GBR output)

## Evaluation Standards (match notebook results)
- Regression: R² > 0.95, check CV stability (std < 0.01)
- Anomaly detection: F1 > 0.85, ROC-AUC > 0.95
- Report: precision, recall, F1, confusion matrix, feature importance
- Always use `test_size=0.2, random_state=42` for reproducibility

## Notebook → Production Pattern
1. Train + evaluate in `notebooks/`
2. Save model: `joblib.dump()` → `notebooks/models/`
3. Copy to `services/ai-service/models/`
4. Add inference endpoint in `services/ai-service/main.py`
5. Add pipeline step in `services/pipeline-worker/worker/__main__.py`
6. Register in `model_registry` table
