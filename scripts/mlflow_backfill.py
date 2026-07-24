#!/usr/bin/env python3
"""Backfill MLflow with the real v3.0 model runs, artifacts, and registry entries.

The v3.0 models were trained in notebooks without MLflow instrumentation, so the
tracking server and its MinIO artifact bucket were empty. This script logs the models
that already exist on disk — their honest metrics (from notebooks/models/metrics.json),
their hyperparameters (from the *_model_card.md files), and the actual serialized
artifacts — into MLflow experiments and the model registry.

Nothing here is fabricated: every metric is read from the generated metrics.json, every
artifact is an existing file. Re-running is idempotent-friendly (creates a new run each
time but reuses the named experiments and registered models).

Run from the repo root with the project venv:
    .venv/bin/python scripts/mlflow_backfill.py
"""

import json
import os
import re
from pathlib import Path

# ── Point the client at the local stack (host-side ports) ─────────────────────
os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")
os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "minio")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "minio_pw")

import mlflow
from mlflow.tracking import MlflowClient

REPO = Path(__file__).resolve().parent.parent
MODELS = REPO / "notebooks" / "models"
METRICS = json.loads((MODELS / "metrics.json").read_text())["models"]

# ── One entry per production model: where its files live and how to register it ──
MODEL_SPECS = {
    "cem_score": {
        "experiment": "CEM Experience Score",
        "registered_name": "cem-experience-score",
        "artifact": "cem_v3_lightgbm.joblib",
        "feature_names": "cem_v3_feature_names.joblib",
        "card": "cem_v3_model_card.md",
    },
    "oss_anomaly": {
        "experiment": "OSS Experience Anomaly",
        "registered_name": "oss-experience-anomaly",
        "artifact": "oss_vae_v3.pt",
        "feature_names": "vae_v3_feature_names.joblib",
        "card": "oss_vae_v3_model_card.md",
    },
    "rat_underservice": {
        "experiment": "RAT Underservice",
        "registered_name": "rat-underservice",
        "artifact": "rat_underservice_v3_xgb.joblib",
        "feature_names": "rat_v3_feature_names.joblib",
        "card": "rat_underservice_v3_model_card.md",
    },
}


def flatten(prefix, obj, metrics, params):
    """Split a nested dict into flat numeric metrics and string params."""
    for key, val in obj.items():
        name = f"{prefix}{key}" if prefix else key
        if isinstance(val, dict):
            flatten(f"{name}_", val, metrics, params)
        elif isinstance(val, (int, float)) and not isinstance(val, bool):
            metrics[name] = float(val)
        elif isinstance(val, list):
            params[name] = ", ".join(map(str, val))[:250]
        else:
            params[name] = str(val)[:250]


def parse_card_hyperparams(card_text):
    """Pull XGBoost-style 'key=value' hyperparameters out of a model card."""
    found = {}
    for k, v in re.findall(r"(\w+)\s*=\s*([0-9.]+)", card_text):
        found[f"hp_{k}"] = v
    return found


def main():
    client = MlflowClient()
    print(
        f"Tracking: {os.environ['MLFLOW_TRACKING_URI']}  "
        f"Artifacts via: {os.environ['MLFLOW_S3_ENDPOINT_URL']}\n"
    )

    for model_key, spec in MODEL_SPECS.items():
        meta = METRICS[model_key]
        mlflow.set_experiment(spec["experiment"])

        # Metrics = the honest numbers; params = everything descriptive.
        metrics, params = {}, {}
        flatten("", meta.get("metrics", {}), metrics, params)
        for pk in (
            "name",
            "algorithm",
            "version",
            "task",
            "features",
            "featureNames",
            "lastTrained",
            "source",
        ):
            if pk in meta:
                val = meta[pk]
                params[pk] = (
                    ", ".join(map(str, val)) if isinstance(val, list) else str(val)
                )[:250]
        flatten("train_", meta.get("trainingData", {}), metrics, params)

        card_path = MODELS / spec["card"]
        if card_path.exists():
            params.update(parse_card_hyperparams(card_path.read_text()))

        with mlflow.start_run(run_name=f"{model_key}-v3.0") as run:
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)
            # Real serialized artifacts → MinIO.
            mlflow.log_artifact(str(MODELS / spec["artifact"]), artifact_path="model")
            fn = MODELS / spec["feature_names"]
            if fn.exists():
                mlflow.log_artifact(str(fn), artifact_path="model")
            if card_path.exists():
                mlflow.log_artifact(str(card_path), artifact_path="cards")

            run_id = run.info.run_id
            print(
                f"  [{spec['experiment']}] run {run_id[:8]} — "
                f"{len(metrics)} metrics, {len(params)} params logged"
            )

        # Register + promote to Production so the registry page shows a real stage.
        model_uri = f"runs:/{run_id}/model"
        mv = mlflow.register_model(model_uri, spec["registered_name"])
        client.transition_model_version_stage(
            name=spec["registered_name"], version=mv.version, stage="Production"
        )
        print(f"    registered {spec['registered_name']} v{mv.version} → Production\n")

    print("Backfill complete.")


if __name__ == "__main__":
    main()
