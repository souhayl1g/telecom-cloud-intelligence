"""MLflow REST API proxy — exposes experiment tracking + model registry to the dashboard.

Uses stdlib urllib (no extra deps) to forward calls to the MLflow tracking server.
Requires the mlflow service to be running (docker compose includes it by default).
Returns null/empty gracefully when MLflow is unreachable so the page degrades honestly.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends

from auth import require_role

router = APIRouter()

MLFLOW_URL = os.getenv("MLFLOW_URL", "http://mlflow:5000")
_BASE = f"{MLFLOW_URL}/api/2.0/mlflow"


def _mlflow_post(path: str, body: dict) -> dict:
    """POST to MLflow REST API; returns {} on any network/parse failure."""
    try:
        req = urllib.request.Request(
            f"{_BASE}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def _mlflow_get(path: str, params: dict | None = None) -> dict:
    """GET from MLflow REST API; returns {} on any network/parse failure.

    Some MLflow 2.x search endpoints (notably registered-models/search) are GET-only
    and reject POST with HTTP 405, unlike experiments/runs search which are POST.
    """
    try:
        url = f"{_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}


@router.get("/mlflow/summary")
def mlflow_summary(user=Depends(require_role("data_scientist"))):
    """Experiments + recent runs + registered models (single dashboard request)."""
    # MLflow 2.x uses /search (POST) — /list was removed in v2.
    experiments = _mlflow_post("/experiments/search", {"max_results": 100}).get(
        "experiments", []
    )

    # Most recent 20 runs across all experiments, ordered by start time.
    # MLflow 2.x runs/search REQUIRES experiment_ids — omitting it returns zero runs.
    exp_ids = [e.get("experiment_id") for e in experiments if e.get("experiment_id")]
    runs_raw = (
        _mlflow_post(
            "/runs/search",
            {
                "experiment_ids": exp_ids,
                "max_results": 20,
                "order_by": ["start_time DESC"],
            },
        ).get("runs", [])
        if exp_ids
        else []
    )

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

    # MLflow 2.x: registered-models/search replaces /list — and is GET-only
    # (POST returns HTTP 405), unlike experiments/runs search above.
    models = _mlflow_get("/registered-models/search", {"max_results": 100}).get(
        "registered_models", []
    )
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
