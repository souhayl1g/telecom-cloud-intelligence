"""retrain-service — execute ML training notebooks on demand via papermill.

POST /retrain  body: { model_name: 'cem'|'rat'|'vae', run_id?, params: {...} }
GET  /retrain/{run_id}/status
GET  /health
"""

from __future__ import annotations

import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional

import boto3
import papermill as pm
from botocore.client import Config
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from auth import require_internal_auth

NOTEBOOKS_DIR = Path(os.getenv("NOTEBOOKS_DIR", "/notebooks"))
MODELS_OUTPUT_DIR = Path(os.getenv("MODELS_OUTPUT_DIR", "/models"))
WORK_DIR = Path(os.getenv("RETRAIN_WORK_DIR", "/tmp/retrain"))
WORK_DIR.mkdir(parents=True, exist_ok=True)

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minio")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minio_pw")
RETRAIN_BUCKET = os.getenv("RETRAIN_BUCKET", "retrain-runs")

# notebook → expected output artifact name in notebooks/models/
# notebook → expected output artifact name in notebooks/models/
# Must match the filenames in ai-service/config.py.
NOTEBOOK_MAP = {
    "cem": ("02_cem_score_training.ipynb", "cem_v3_lightgbm.joblib"),
    "rat": ("04_rat_underservice_training.ipynb", "rat_underservice_v3_xgb.joblib"),
    "vae": ("03_oss_vae_anomaly_training.ipynb", "oss_vae_v3.pt"),
}

# In-memory status registry — survives within a single container lifetime
_RUNS: dict[str, dict] = {}

app = FastAPI(title="NeXo Retrain Service", version="1.0")


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


def _ensure_bucket(bucket: str) -> None:
    s3 = _s3()
    try:
        existing = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
        if bucket not in existing:
            s3.create_bucket(Bucket=bucket)
    except Exception as e:
        print(f"[retrain] ensure_bucket({bucket}) failed: {e}")


def _upload_notebook(local_path: Path, run_id: str, model_name: str) -> str:
    _ensure_bucket(RETRAIN_BUCKET)
    s3 = _s3()
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"{date_prefix}/{model_name}/{run_id}.ipynb"
    with open(local_path, "rb") as f:
        body = f.read()
    s3.put_object(
        Bucket=RETRAIN_BUCKET,
        Key=key,
        Body=BytesIO(body),
        ContentLength=len(body),
        ContentType="application/x-ipynb+json",
    )
    return key


def _copy_artifact(model_name: str) -> Optional[str]:
    """Copy trained artifact from notebooks/models/ to MODELS_OUTPUT_DIR."""
    _, artifact_name = NOTEBOOK_MAP[model_name]
    src_candidates = [
        NOTEBOOKS_DIR / "models" / artifact_name,
        Path("/app/notebooks/models") / artifact_name,
        Path("/notebooks/models") / artifact_name,
    ]
    src = next((p for p in src_candidates if p.exists()), None)
    if not src:
        return None
    MODELS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = MODELS_OUTPUT_DIR / artifact_name
    shutil.copy2(src, dst)
    # Also copy the VAE scaler when retraining VAE
    if model_name == "vae":
        scaler_src = src.parent / "vae_v3_scaler.joblib"
        if scaler_src.exists():
            shutil.copy2(scaler_src, MODELS_OUTPUT_DIR / "vae_v3_scaler.joblib")
    return str(dst)


class RetrainRequest(BaseModel):
    model_name: str = Field(..., description="'cem' | 'rat' | 'vae'")
    run_id: Optional[str] = None
    params: dict = Field(default_factory=dict)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "notebooks_dir_exists": NOTEBOOKS_DIR.exists(),
        "models_output_dir_exists": MODELS_OUTPUT_DIR.exists(),
        "active_runs": len([r for r in _RUNS.values() if r["status"] == "running"]),
        "total_runs": len(_RUNS),
    }


@app.get("/retrain/{run_id}/status")
def status(run_id: str, _=Depends(require_internal_auth)):
    row = _RUNS.get(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="run_id not found")
    return row


@app.post("/retrain")
def retrain(req: RetrainRequest, _=Depends(require_internal_auth)):
    if req.model_name not in NOTEBOOK_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"model_name must be one of {list(NOTEBOOK_MAP)}",
        )

    notebook_name, _artifact_name = NOTEBOOK_MAP[req.model_name]
    notebook_in = NOTEBOOKS_DIR / notebook_name
    if not notebook_in.exists():
        raise HTTPException(
            status_code=500,
            detail=f"input notebook not found: {notebook_in}",
        )

    run_id = req.run_id or f"retrain-{uuid.uuid4().hex[:12]}"
    started = time.time()
    notebook_out = WORK_DIR / f"{run_id}.ipynb"

    _RUNS[run_id] = {
        "run_id": run_id,
        "model_name": req.model_name,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        pm.execute_notebook(
            input_path=str(notebook_in),
            output_path=str(notebook_out),
            parameters=req.params or {},
            kernel_name=os.getenv("PAPERMILL_KERNEL", "python3"),
            progress_bar=False,
            log_output=True,
            request_save_on_cell_execute=True,
        )

        artifact_path = _copy_artifact(req.model_name)
        executed_key = _upload_notebook(notebook_out, run_id, req.model_name)
        elapsed = round(time.time() - started, 2)

        _RUNS[run_id].update(
            {
                "status": "succeeded",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": elapsed,
                "model_artifact_path": artifact_path,
                "executed_notebook_minio_key": executed_key,
            }
        )
        return _RUNS[run_id]

    except Exception as e:
        elapsed = round(time.time() - started, 2)
        executed_key = None
        try:
            if notebook_out.exists():
                executed_key = _upload_notebook(notebook_out, run_id, req.model_name)
        except Exception as up_err:
            print(f"[retrain] failed to upload partial notebook: {up_err}")
        _RUNS[run_id].update(
            {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": elapsed,
                "error": str(e)[:500],
                "executed_notebook_minio_key": executed_key,
            }
        )
        return _RUNS[run_id]
