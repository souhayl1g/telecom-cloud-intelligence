"""
Bootstrap default ML models if none exist in /app/models/.
This ensures ai-service can start even before notebooks train models.
Models will be replaced by notebook-trained versions once available.
"""

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODELS_DIR = Path("/app/models")


def bootstrap():
    MODELS_DIR.mkdir(exist_ok=True)
    needed = []

    if not (MODELS_DIR / "sla_risk_model.joblib").exists():
        needed.append("sla")
    if not (MODELS_DIR / "anomaly_model.joblib").exists():
        needed.append("oss")
    if not (MODELS_DIR / "cem_anomaly_model.joblib").exists():
        needed.append("bss")

    if not needed:
        print("[bootstrap] All models present, skipping.")
        return

    print(f"[bootstrap] Training default models: {needed}")
    np.random.seed(42)
    n = 2000

    if "sla" in needed:
        X = np.column_stack(
            [
                np.random.uniform(20, 150, n),
                np.random.uniform(2, 40, n),
                np.random.uniform(5, 100, n),
                np.random.uniform(1, 30, n),
                np.random.uniform(10, 200, n),
                np.random.uniform(0, 5, n),
                np.random.uniform(0, 15, n),
                np.random.uniform(50, 500, n),
                np.random.uniform(-120, -60, n),
            ]
        )
        y = (X[:, 2] * 0.008 + X[:, 5] * 0.10 + np.random.randn(n) * 0.05).clip(0, 1)
        pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    GradientBoostingRegressor(
                        n_estimators=200, max_depth=4, random_state=42
                    ),
                ),
            ]
        )
        pipe.fit(X, y)
        joblib.dump(pipe, MODELS_DIR / "sla_risk_model.joblib")
        print("[bootstrap] sla_risk_model.joblib created")

    if "oss" in needed:
        X = np.column_stack(
            [
                np.random.uniform(20, 150, n),
                np.random.uniform(5, 50, n),
                np.random.uniform(0, 3, n),
                np.random.randint(50, 500, n).astype(float),
                np.random.uniform(-110, -70, n),
            ]
        )
        pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    IsolationForest(
                        n_estimators=150, contamination=0.05, random_state=42
                    ),
                ),
            ]
        )
        pipe.fit(X)
        joblib.dump(pipe, MODELS_DIR / "anomaly_model.joblib")
        print("[bootstrap] anomaly_model.joblib created")

    if "bss" in needed:
        X = np.column_stack(
            [
                np.random.uniform(10, 80, n),
                np.random.uniform(0.5, 30, n),
                np.random.uniform(10, 500, n),
                np.random.randint(0, 100, n).astype(float),
                np.random.uniform(0, 0.3, n),
            ]
        )
        pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    IsolationForest(
                        n_estimators=150, contamination=0.05, random_state=42
                    ),
                ),
            ]
        )
        pipe.fit(X)
        joblib.dump(pipe, MODELS_DIR / "cem_anomaly_model.joblib")
        print("[bootstrap] cem_anomaly_model.joblib created")

    print("[bootstrap] Done.")


if __name__ == "__main__":
    bootstrap()
