# AI Models Documentation

## 1. Source of truth

The current implementation lives in:

- `services/ai-service/main.py`
- `services/ai-service/requirements.txt`

The service trains models on startup only when the persisted artifacts do not already exist. After training, it writes them to `/app/models/` as joblib files and reloads them on later restarts.

Current implementation constants:

- `MODEL_VERSION = "v2.0"`
- `N_TRAIN = 3000`
- `RANDOM_SEED = 42`
- `scikit-learn == 1.5.2` inside the ai-service container

This matters for tuning: if you change hyperparameters in code but keep the existing persisted model files, the service will keep loading the old fitted models instead of retraining.

## 2. Why these 3 models exactly

This project has 3 different ML tasks, not 1:

1. Predict a continuous SLA risk score from aggregated OSS KPIs.
2. Detect anomalous OSS records without labels.
3. Detect anomalous BSS revenue and usage records without labels.

Because the tasks are different, the model families should also be different.

| Task | Model | Why this is a good fit |
| --- | --- | --- |
| SLA risk prediction | `GradientBoostingRegressor` | Small tabular numeric dataset, non-linear KPI interactions, interpretable feature importances, strong performance on structured data |
| OSS anomaly detection | `IsolationForest` | Unsupervised anomaly detection, numeric tabular data, robust when anomalies are rare and labels are unavailable |
| BSS anomaly detection | `IsolationForest` | Same anomaly-detection problem shape as OSS, but with business metrics instead of network metrics |

### Why not one single model for everything?

Because the outputs are different:

- SLA risk is a regression problem: output is a score between `0.0` and `1.0`.
- OSS anomaly detection is an unsupervised outlier problem: output is normal vs anomalous plus an anomaly score.
- BSS anomaly detection is also an unsupervised outlier problem, but on a different feature space.

A single model would be technically weaker and harder to justify.

## 3. Parameters vs hyperparameters

This distinction matters.

### Hyperparameters

These are chosen before training. Examples:

- `n_estimators`
- `max_depth`
- `learning_rate`
- `subsample`
- `contamination`
- `max_samples`
- `max_features`
- `random_state`

These are the values you tune to improve performance.

### Learned parameters

These are produced by the training process itself.

Examples:

- Tree split thresholds
- Leaf values
- Feature usage patterns inside the ensemble
- Internal anomaly score boundaries

You do not manually tune learned parameters. The algorithm learns them from data.

## 4. Model 1: SLA Risk Scorer

### 4.1 Business objective

Predict the risk that the current KPI window will violate SLA expectations.

Output:

- A continuous score in `[0.0, 1.0]`
- Feature importances for explainability

### 4.2 Why `GradientBoostingRegressor`

This is the right choice for the current project because:

- The data is tabular and numeric.
- The training set is relatively small: `3000` synthetic windows.
- SLA risk is non-linear. For example, latency effects are not linear across the full range.
- KPI interactions matter. High latency plus packet loss is worse than either metric alone.
- The model gives `feature_importances_`, which is useful for explanation during the PFE defense.
- It is much simpler to defend academically than a neural network for this dataset size.

### 4.3 Why not linear regression?

Linear regression assumes a mostly linear relationship between inputs and target. That is not what your label construction does.

Your synthetic risk label is threshold-driven and clipped:

- latency contributes risk only after a threshold
- throughput contributes risk only when it becomes too low
- packet loss ramps up non-linearly

Gradient boosting models these effects much better.

### 4.4 Why not a neural network?

You could use one, but it is not the pragmatic choice here:

- dataset is small for neural-network standards
- weaker explainability for the jury
- more tuning overhead
- higher risk of unstable behavior on synthetic data

### 4.5 Current input features

The model is trained on these 9 aggregated OSS features:

- `mean_throughput_mbps`
- `std_throughput_mbps`
- `mean_latency_ms`
- `std_latency_ms`
- `max_latency_ms`
- `mean_packet_loss_pct`
- `max_packet_loss_pct`
- `mean_active_users`
- `mean_signal_rsrp_dbm`

### 4.6 Current target

The target is a synthetic deterministic risk label built from the aggregated KPIs.

Current label logic in code:

```python
risk += clip((mean_lat - 20) / 60,  0, 0.35)
risk += clip((max_lat  - 30) / 70,  0, 0.25)
risk += clip(mean_loss / 4,         0, 0.25)
risk += clip(max_loss  / 6,         0, 0.15)
risk += clip((60 - mean_tput) / 100, 0, 0.20)
risk += noise(0, 0.03)
```

So the model is learning a telecom-inspired risk function rather than random labels.

### 4.7 Current training pipeline

```python
Pipeline([
    ("scaler", StandardScaler()),
    ("gbr", GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
    )),
])
```

### 4.8 Current explicit hyperparameters

| Hyperparameter | Current value | Meaning | Typical effect |
| --- | --- | --- | --- |
| `n_estimators` | `200` | Number of boosting stages / trees | More trees can improve fit, but too many can overfit and increase training time |
| `max_depth` | `4` | Depth of each weak tree | Higher depth learns more complex interactions, but overfits faster |
| `learning_rate` | `0.05` | Contribution of each tree | Lower values are often more stable, but need more trees |
| `subsample` | `0.8` | Fraction of samples used per boosting stage | Adds stochasticity and often improves generalization |
| `random_state` | `42` | Reproducibility seed | Keeps experiments repeatable |

### 4.9 Important model hyperparameters not explicitly set yet

These still use scikit-learn defaults for the pinned version in the service container:

- `loss`
- `min_samples_split`
- `min_samples_leaf`
- `max_features`
- `validation_fraction`
- `n_iter_no_change`
- `tol`
- `criterion`
- `ccp_alpha`

These are valid tuning candidates.

### 4.10 Best hyperparameters to tune first

If you want the biggest return on effort, tune these first:

1. `learning_rate`
2. `n_estimators`
3. `max_depth`
4. `subsample`
5. `min_samples_leaf`
6. `max_features`

Recommended search space:

| Hyperparameter | Good search range |
| --- | --- |
| `learning_rate` | `0.01`, `0.03`, `0.05`, `0.1`, `0.2` |
| `n_estimators` | `100` to `500` |
| `max_depth` | `2` to `6` |
| `subsample` | `0.6`, `0.8`, `1.0` |
| `min_samples_leaf` | `1`, `2`, `5`, `10` |
| `max_features` | `None`, `"sqrt"`, `0.7` |

### 4.11 How to judge whether tuning helped

For this model, use supervised regression metrics on a holdout set:

- MAE
- RMSE
- `R^2`

Because the target is a risk score in `[0, 1]`, MAE is usually the easiest metric to explain.

## 5. Model 2: OSS Anomaly Detector

### 5.1 Business objective

Detect abnormal network KPI records such as:

- throughput collapse
- latency spikes
- packet loss surge
- overload situations
- very weak signal conditions

### 5.2 Why `IsolationForest`

This is a strong fit because:

- anomaly labels are usually unavailable in real telecom operations
- the data is numeric and tabular
- anomalies are rare compared with normal observations
- the method is simple, fast, and standard for unsupervised outlier detection
- it naturally produces anomaly decisions and anomaly scores

### 5.3 Why not classification here?

Classification would require labeled normal vs anomalous records. The current project does not store a real labeled anomaly dataset for OSS.

That makes an unsupervised detector the correct design choice for the current maturity level of the platform.

### 5.4 Current input features

The OSS anomaly model uses 5 per-record features:

- `throughput_mbps`
- `latency_ms`
- `packet_loss_pct`
- `active_users`
- `signal_rsrp_dbm`

### 5.5 Current training data assumptions

Synthetic training distribution:

- `95%` normal records
- `5%` anomalous records

Injected anomaly patterns include:

- very low throughput
- very high latency
- high packet loss
- overloaded active-user counts
- very weak signal strength

### 5.6 Current training pipeline

```python
Pipeline([
    ("scaler", StandardScaler()),
    ("ifo", IsolationForest(
        n_estimators=150,
        contamination=0.05,
        random_state=42,
    )),
])
```

### 5.7 Current explicit hyperparameters

| Hyperparameter | Current value | Meaning | Typical effect |
| --- | --- | --- | --- |
| `n_estimators` | `150` | Number of isolation trees | More trees improve score stability but cost more compute |
| `contamination` | `0.05` | Expected anomaly fraction | Strongly affects the anomaly threshold |
| `random_state` | `42` | Reproducibility seed | Keeps experiments repeatable |

### 5.8 Important hyperparameters not explicitly set yet

These still follow scikit-learn defaults for the pinned version:

- `max_samples`
- `max_features`
- `bootstrap`
- `warm_start`
- `n_jobs`

### 5.9 Best hyperparameters to tune first

For `IsolationForest`, tune these first:

1. `contamination`
2. `n_estimators`
3. `max_samples`
4. `max_features`

Recommended search space:

| Hyperparameter | Good search range |
| --- | --- |
| `contamination` | `0.01`, `0.03`, `0.05`, `0.08`, `0.1` |
| `n_estimators` | `100`, `150`, `200`, `300` |
| `max_samples` | `128`, `256`, `512`, `"auto"` |
| `max_features` | `0.6`, `0.8`, `1.0` |

### 5.10 Most sensitive hyperparameter: `contamination`

This is usually the most important setting in `IsolationForest`.

- If it is too low, the model misses true anomalies.
- If it is too high, the model flags too many normal records.

Because your synthetic training mix is `95%` normal and `5%` anomalous, the current value `0.05` is consistent with the generated data.

## 6. Model 3: BSS Revenue Anomaly Detector

### 6.1 Business objective

Detect anomalous subscriber-level business behavior such as:

- abnormal recharge amounts
- abnormal usage patterns
- dormant SIM behavior
- spam-like SMS volumes
- possible SIM-box-like voice patterns
- abrupt churn-risk spikes

### 6.2 Why `IsolationForest` again

It is used again because the problem type is again unsupervised anomaly detection.

The feature space is different from OSS, but the modeling need is the same:

- anomaly labels are not guaranteed
- anomalies are rare
- you need anomaly scores, not only hard labels
- model must stay simple and explainable

### 6.3 Current input features

The BSS anomaly model uses 5 per-record business features:

- `revenue_tnd`
- `data_used_gb`
- `voice_min`
- `sms_count`
- `churn_risk`

### 6.4 Current training data assumptions

Synthetic training distribution:

- `95%` normal records
- `5%` anomalous records

Normal behavior covers a Tunisian-style revenue and usage distribution.

Injected anomaly patterns include:

- dormant SIM behavior with near-zero revenue and voice
- very high recharge values
- excessive voice usage consistent with SIM-box-like traffic
- SMS spam behavior
- very high churn risk

### 6.5 Current training pipeline

```python
Pipeline([
    ("scaler", StandardScaler()),
    ("ifo", IsolationForest(
        n_estimators=150,
        contamination=0.05,
        random_state=42,
    )),
])
```

### 6.6 Current explicit hyperparameters

They are the same as the OSS anomaly model:

- `n_estimators = 150`
- `contamination = 0.05`
- `random_state = 42`

### 6.7 Best hyperparameters to tune first

Same priority as the OSS anomaly model:

1. `contamination`
2. `n_estimators`
3. `max_samples`
4. `max_features`

The best values may still be different from the OSS model because the BSS data distribution is different.

## 7. About `StandardScaler` in all 3 pipelines

Each model is wrapped in a `Pipeline` with `StandardScaler` first.

Important note:

- Tree-based methods usually do not need feature scaling.
- `GradientBoostingRegressor` and `IsolationForest` are both tree-based.

So the scaler is not the reason these models work. It mostly provides pipeline consistency. You can keep it, but it is not the main performance lever for these estimators.

## 8. Can you modify parameters and hyperparameters during training?

### Short answer

Yes, you can modify hyperparameters for future training runs.

No, you generally should not think of scikit-learn training as something where you change hyperparameters live in the middle of one `fit()` call.

### What is possible in this project

You can:

- change hyperparameters in code before training starts
- rerun training with new values
- compare results across runs
- keep the best configuration

### What is not the normal workflow

You should not try to:

- change `max_depth` halfway through a running fit
- change `contamination` halfway through a running fit
- mutate the estimator live and expect a correct incremental result

For these scikit-learn estimators, the right workflow is repeated training runs, not live hyperparameter mutation.

## 9. Very important for this codebase: retraining is cached

The ai-service does this on startup:

1. If model artifact exists, load it.
2. Otherwise, train and save it.

That means after changing hyperparameters you must force retraining.

### If you do not force retraining

The service will keep loading the old models from:

- `/app/models/sla_risk_model.joblib`
- `/app/models/anomaly_model.joblib`
- `/app/models/revenue_anomaly_model.joblib`

### How to force retraining safely

Use one of these methods:

1. Delete the persisted model artifacts and restart `ai-service`.
2. Change the artifact filenames or model versioning logic.
3. Clear the Docker volume that stores `/app/models/`.

If you tune hyperparameters often, option 2 is the safest because it keeps experiment history cleaner.

## 10. Recommended tuning workflow for best results

### For the SLA model

Use a supervised tuning workflow:

1. Split synthetic windows into train and validation sets.
2. Search across `learning_rate`, `n_estimators`, `max_depth`, `subsample`, and `min_samples_leaf`.
3. Evaluate with MAE and RMSE.
4. Keep the best run.
5. Retrain on the full training set with the best configuration.

Example approach:

```python
from sklearn.model_selection import RandomizedSearchCV

param_dist = {
    "gbr__n_estimators": [100, 200, 300, 500],
    "gbr__learning_rate": [0.01, 0.03, 0.05, 0.1, 0.2],
    "gbr__max_depth": [2, 3, 4, 5, 6],
    "gbr__subsample": [0.6, 0.8, 1.0],
    "gbr__min_samples_leaf": [1, 2, 5, 10],
}

search = RandomizedSearchCV(
    estimator=pipe,
    param_distributions=param_dist,
    n_iter=20,
    scoring="neg_mean_absolute_error",
    cv=5,
    n_jobs=-1,
    random_state=42,
)

search.fit(X, y)
best_model = search.best_estimator_
```

### For the anomaly models

Tuning is harder because these are unsupervised.

Best practice:

1. Build a labeled validation dataset if possible.
2. Tune `contamination`, `n_estimators`, `max_samples`, `max_features`.
3. Evaluate using precision, recall, F1, or top-k review quality.

If you do not have labels, use a proxy workflow:

1. Inject known synthetic anomalies into a validation set.
2. Measure how many are detected.
3. Measure false positive rate on normal samples.
4. Choose the best tradeoff.

Simple manual search example:

```python
configs = [
    {"n_estimators": 100, "contamination": 0.03},
    {"n_estimators": 150, "contamination": 0.05},
    {"n_estimators": 300, "contamination": 0.08},
]

for cfg in configs:
    model = IsolationForest(
        n_estimators=cfg["n_estimators"],
        contamination=cfg["contamination"],
        random_state=42,
    )
    model.fit(X_train)
    # score on labeled or synthetic validation data
```

## 11. Where to change the hyperparameters in the current code

Edit these functions in `services/ai-service/main.py`:

- `_train_sla_model()`
- `_train_anomaly_model()`
- `_train_revenue_anomaly_model()`

That is where the estimator constructors are defined.

## 12. Practical recommendations for this project

If the goal is better results with minimal complexity, do this in order:

1. Add an explicit train/validation split for the SLA model.
2. Tune the SLA model first, because it is the most straightforward to evaluate.
3. Build a labeled anomaly validation set for OSS and BSS.
4. Tune `contamination` carefully for both `IsolationForest` models.
5. Add experiment logging so each tuning run records hyperparameters and metrics.

## 13. Bottom line

- `GradientBoostingRegressor` is used because SLA risk is a small tabular regression problem with non-linear behavior.
- `IsolationForest` is used twice because both OSS and BSS anomaly detection are unsupervised rare-event problems.
- Yes, you can modify hyperparameters to improve results.
- No, you should not modify them in the middle of one running fit.
- In this codebase, changing hyperparameters requires forcing retraining because fitted models are cached on disk.