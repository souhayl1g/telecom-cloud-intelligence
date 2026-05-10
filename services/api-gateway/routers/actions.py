from fastapi import APIRouter, HTTPException, Query, Depends, Body
from psycopg2.extras import RealDictCursor, Json
import requests
from db import _db
from auth import require_auth
from config import AI_SERVICE_URL

router = APIRouter()


@router.get("/actions")
def list_actions(
    limit: int = Query(default=50, ge=1, le=500),
    status: str = Query(default=None),
    user=Depends(require_auth),
):
    """List agent actions, optionally filtered by status."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if status:
                    cur.execute(
                        """
                        SELECT * FROM agent_actions
                        WHERE status = %s
                        ORDER BY created_at DESC LIMIT %s;
                        """,
                        (status, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM agent_actions
                        ORDER BY created_at DESC LIMIT %s;
                        """,
                        (limit,),
                    )
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions")
def create_action(action: dict = Body(...), user=Depends(require_auth)):
    """Persist a new agent action."""
    required = ["action_id", "type", "title", "severity"]
    for field in required:
        if field not in action:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO agent_actions
                        (action_id, type, title, description, severity, status,
                         source, confidence, impact, playbook_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (action_id) DO NOTHING
                    RETURNING *;
                    """,
                    (
                        action["action_id"],
                        action["type"],
                        action["title"],
                        action.get("description"),
                        action["severity"],
                        action.get("status", "pending"),
                        action.get("source"),
                        action.get("confidence"),
                        action.get("impact"),
                        action.get("playbook_id"),
                    ),
                )
                row = cur.fetchone()
                if not row:
                    # Already exists — return the existing one
                    cur.execute(
                        "SELECT * FROM agent_actions WHERE action_id = %s;",
                        (action["action_id"],),
                    )
                    row = cur.fetchone()
                return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/actions/{action_id}")
def update_action(action_id: str, body: dict = Body(...), user=Depends(require_auth)):
    """Update action status (approve/reject)."""
    new_status = body.get("status")
    if new_status not in ("approved", "rejected", "executed", "auto_approved"):
        raise HTTPException(status_code=400, detail="Invalid status")
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE agent_actions
                    SET status = %s,
                        resolved_at = CASE WHEN %s IN ('approved','rejected','executed') THEN now() ELSE resolved_at END,
                        resolved_by = %s
                    WHERE action_id = %s
                    RETURNING *;
                    """,
                    (
                        new_status,
                        new_status,
                        user.get("sub", "system"),
                        action_id,
                    ),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Action not found")
                return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/execute")
def execute_action(action_id: str, user=Depends(require_auth)):
    """Execute the playbook associated with an action. Returns real execution results."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM agent_actions WHERE action_id = %s;",
                    (action_id,),
                )
                action = cur.fetchone()
                if not action:
                    raise HTTPException(status_code=404, detail="Action not found")

                playbook_id = action.get("playbook_id")
                execution_log = {"playbook_id": playbook_id, "steps": []}

                # ── pb-model-retrain ──────────────────────────────────────
                if playbook_id == "pb-model-retrain":
                    try:
                        r = requests.post(
                            f"{AI_SERVICE_URL}/models/reload", timeout=15
                        )
                        r.raise_for_status()
                        reload_result = r.json()
                        execution_log["steps"].append(
                            {"step": "Force-reload ML models", "result": reload_result}
                        )
                    except Exception as e:
                        execution_log["steps"].append(
                            {"step": "Force-reload ML models", "error": str(e)}
                        )

                # ── pb-anomaly-triage ─────────────────────────────────────
                elif playbook_id == "pb-anomaly-triage":
                    cur.execute(
                        """
                        SELECT cell_id, area, cell_load_pct, latency_ms, packet_loss_rate
                        FROM oss_cell_kpis
                        WHERE anomaly_flag = TRUE AND created_at >= NOW() - INTERVAL '30 minutes'
                        ORDER BY cell_load_pct DESC LIMIT 50;
                        """
                    )
                    recent = cur.fetchall()
                    critical = [r for r in recent if (r["cell_load_pct"] or 0) > 80]
                    warning = [r for r in recent if 50 < (r["cell_load_pct"] or 0) <= 80]
                    low = [r for r in recent if (r["cell_load_pct"] or 0) <= 50]
                    cells_affected = list({r["cell_id"] for r in critical if r["cell_id"]})

                    # Cross-reference with Granger causality for root cause
                    cur.execute(
                        """
                        SELECT oss_variable, cem_variable, best_lag, best_pvalue
                        FROM granger_causality_results
                        WHERE significant = TRUE
                        ORDER BY best_pvalue ASC LIMIT 10;
                        """
                    )
                    strong_granger = cur.fetchall()

                    execution_log["steps"] = [
                        {"step": "Collect recent anomalies", "count": len(recent)},
                        {
                            "step": "Classify by severity",
                            "critical": len(critical),
                            "warning": len(warning),
                            "low": len(low),
                        },
                        {"step": "Identify affected cells", "cells": cells_affected},
                        {
                            "step": "Cross-reference Granger causality for root cause",
                            "strong_pairs": [
                                {
                                    "pair": f"{c['oss_variable']} → {c['cem_variable']}",
                                    "lag": c["best_lag"],
                                    "pvalue": float(c["best_pvalue"]),
                                }
                                for c in strong_granger
                            ],
                        },
                        {"step": "Triage complete", "priority": "P1" if critical else "P2"},
                    ]

                # ── pb-revenue-protect ────────────────────────────────────
                elif playbook_id == "pb-revenue-protect":
                    cur.execute(
                        """
                        SELECT imsi_hash, rat_gap_score, cem_score, churn_risk_flag
                        FROM subscriber_features
                        WHERE (rat_gap_score > 0.3 OR churn_risk_flag = TRUE)
                          AND created_at >= NOW() - INTERVAL '30 minutes'
                        ORDER BY rat_gap_score DESC NULLS LAST LIMIT 20;
                        """
                    )
                    flagged = cur.fetchall()
                    execution_log["steps"] = [
                        {"step": "Query high-risk subscribers", "count": len(flagged)},
                        {
                            "step": "Flag suspicious subscribers",
                            "subscribers": [
                                {
                                    "id": r["imsi_hash"],
                                    "rat_gap_score": float(r["rat_gap_score"]) if r["rat_gap_score"] else None,
                                    "cem_score": float(r["cem_score"]) if r["cem_score"] else None,
                                    "churn_risk": r["churn_risk_flag"],
                                }
                                for r in flagged
                            ],
                        },
                        {
                            "step": "Protection summary",
                            "flagged_count": len(flagged),
                            "underserved_count": sum(1 for r in flagged if r["rat_gap_score"] and r["rat_gap_score"] > 0.3),
                            "churn_risk_count": sum(1 for r in flagged if r["churn_risk_flag"]),
                        },
                    ]



                # ── pb-capacity-scale ─────────────────────────────────────
                elif playbook_id == "pb-capacity-scale":
                    cur.execute(
                        """
                        SELECT
                            avg_throughput,
                            avg_latency,
                            avg_packet_loss,
                            subscriber_count,
                            anomaly_count
                        FROM area_network_health
                        ORDER BY created_at DESC LIMIT 10;
                        """
                    )
                    history = cur.fetchall()
                    if history:
                        avg_throughput = sum(r["avg_throughput"] for r in history if r["avg_throughput"] is not None) / max(len([r for r in history if r["avg_throughput"] is not None]), 1)
                        avg_latency = sum(r["avg_latency"] for r in history if r["avg_latency"] is not None) / max(len([r for r in history if r["avg_latency"] is not None]), 1)
                        avg_users = sum(r["subscriber_count"] for r in history if r["subscriber_count"] is not None) / max(len([r for r in history if r["subscriber_count"] is not None]), 1)
                        max_throughput = max((r["avg_throughput"] for r in history if r["avg_throughput"] is not None), default=0)
                        max_users = max((r["subscriber_count"] for r in history if r["subscriber_count"] is not None), default=0)
                        execution_log["steps"] = [
                            {"step": "Compute capacity from recent runs", "runs_analyzed": len(history)},
                            {
                                "step": "Current averages",
                                "throughput_mbps": round(avg_throughput, 2),
                                "active_users": round(avg_users, 0),
                                "latency_ms": round(avg_latency, 2),
                            },
                            {
                                "step": "Peak values observed",
                                "max_throughput_mbps": round(max_throughput, 2),
                                "max_users": round(max_users, 0),
                            },
                            {
                                "step": "Capacity recommendation",
                                "throughput_headroom_pct": round((1 - avg_throughput / max(max_throughput * 1.3, 1)) * 100, 1),
                                "user_headroom_pct": round((1 - avg_users / max(max_users * 1.3, 1)) * 100, 1),
                            },
                        ]
                    else:
                        execution_log["steps"] = [{"step": "No KPI history available"}]

                else:
                    execution_log["steps"] = [{"step": f"Unknown playbook: {playbook_id}"}]

                # Update action with execution log
                cur.execute(
                    """
                    UPDATE agent_actions
                    SET status = 'executed',
                        execution_log = %s,
                        resolved_at = now(),
                        resolved_by = %s
                    WHERE action_id = %s
                    RETURNING *;
                    """,
                    (
                        Json(execution_log),
                        user.get("sub", "system"),
                        action_id,
                    ),
                )
                return cur.fetchone()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
