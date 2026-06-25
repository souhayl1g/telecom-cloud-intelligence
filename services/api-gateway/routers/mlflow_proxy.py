"""MLflow REST API proxy — exposes experiment tracking + model registry to the dashboard.

Uses stdlib urllib (no extra deps) to forward calls to the MLflow tracking server.
Requires the mlflow service to be running (docker compose includes it by default).
Returns null/empty gracefully when MLflow is unreachable so the page degrades honestly.
"""

import json
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends

from auth import require_role

router = APIRouter()

MLFLOW_URL = os.getenv("MLFLOW_URL", "http://mlflow:5000")
_BASE = f"{MLFLOW_URL}/api/2.0/mlflow"


def _mlflow_get(path: str) -> dict:
    """GET from MLflow REST API; returns {} on any network/parse failure."""
    try:
        with urllib.request.urlopen(f"{_BASE}{path}", timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}


@router.get("/mlflow/summary")
def mlflow_summary(user=Depends(require_role("data_scientist"))):
    """Experiments + recent runs + registered models (single dashboard request)."""
    experiments = _mlflow_get("/experiments/list").get("experiments", [])

    # Most recent 20 runs across all experiments, ordered by start time.
    runs_payload = {
        "max_results": 20,
        "order_by": ["start_time DESC"],
    }
    try:
        req = urllib.request.Request(
            f"{_BASE}/runs/search",
            data=json.dumps(runs_payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            runs_raw = json.loads(r.read()).get("runs", [])
    except Exception:
        runs_raw = []

    # Flatten runs to a simple list the UI can render.
    runs = []
    for r in runs_raw:
        info = r.get("info", {})
        metrics = {m["key"]: m["value"] for m in r.get("data", {}).get("metrics", [])}
        params = {p["key"]: p["value"] for p in r.get("data", {}).get("params", [])}
        runs.append(
            {
                "run_id": info.get("run_id", "")[:8],
                "experiment_id": info.get("experiment_id"),
                "status": info.get("status"),
                "start_time": info.get("start_time"),
                "metrics": metrics,
                "params": {k: params[k] for k in list(params)[:5]},
            }
        )

    models = _mlflow_get("/registered-models/list").get("registered_models", [])
    model_summary = [
        {
            "name": m.get("name"),
            "creation_timestamp": m.get("creation_timestamp"),
            "last_updated_timestamp": m.get("last_updated_timestamp"),
            "latest_versions": [
                {
                    "version": v.get("version"),
                    "stage": v.get("current_stage"),
                    "status": v.get("status"),
                }
                for v in (m.get("latest_versions") or [])
            ],
        }
        for m in models
    ]

    return {
        "experiments": [
            {
                "experiment_id": e.get("experiment_id"),
                "name": e.get("name"),
                "lifecycle_stage": e.get("lifecycle_stage"),
            }
            for e in experiments
        ],
        "runs": runs,
        "registered_models": model_summary,
        "mlflow_url": MLFLOW_URL,
        "run_count": len(runs),
    }
