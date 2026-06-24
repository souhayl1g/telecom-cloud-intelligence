"""Admin governance (admin-role only).

Beyond user/role management (auth-service), the admin owns:
  - dashboard settings   : app_settings KV (GET/PATCH)
  - pipeline visibility  : recent pipeline_runs
  - data/model controls  : trigger ai-service model hot-reload

All endpoints require the admin role (enforced server-side via require_role).
"""

import json
import os
import urllib.request

from fastapi import APIRouter, Body, Depends, HTTPException
from psycopg2.extras import RealDictCursor

from db import _db
from auth import require_role

router = APIRouter()

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8001")


@router.get("/admin/settings")
def get_settings(user=Depends(require_role("admin"))):
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT key, value, updated_at, updated_by FROM app_settings ORDER BY key")
            return {"settings": cur.fetchall()}


@router.patch("/admin/settings")
def update_settings(body: dict = Body(...), user=Depends(require_role("admin"))):
    """Upsert each {key: jsonable-value}. Values stored as JSONB."""
    if not body:
        raise HTTPException(status_code=400, detail="No settings provided")
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for key, value in body.items():
                cur.execute(
                    """INSERT INTO app_settings (key, value, updated_by, updated_at)
                       VALUES (%s, %s, %s, now())
                       ON CONFLICT (key) DO UPDATE
                         SET value = EXCLUDED.value, updated_by = EXCLUDED.updated_by, updated_at = now()""",
                    (key, json.dumps(value), user.get("sub", "admin")),
                )
            cur.execute("SELECT key, value, updated_at, updated_by FROM app_settings ORDER BY key")
            return {"settings": cur.fetchall()}


@router.get("/admin/pipeline-status")
def pipeline_status(user=Depends(require_role("admin"))):
    """Recent pipeline runs for the admin operations panel."""
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT run_id, status, started_at, finished_at,
                          EXTRACT(EPOCH FROM (finished_at - started_at))::int AS duration_s
                     FROM pipeline_runs
                    ORDER BY started_at DESC NULLS LAST LIMIT 10"""
            )
            return {"runs": cur.fetchall()}


@router.post("/admin/pipeline/reload-models")
def reload_models(user=Depends(require_role("admin"))):
    """Trigger a real ai-service model hot-reload from disk."""
    try:
        req = urllib.request.Request(f"{AI_SERVICE_URL}/models/reload", method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode("utf-8"))
        return {"status": "ok", "ai_service": body}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ai-service reload failed: {e}")
