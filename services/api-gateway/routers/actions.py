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
                        SELECT severity, cell_id, kpi_name, value, baseline_value
                        FROM anomalies
                        WHERE created_at >= NOW() - INTERVAL '30 minutes'
                        ORDER BY severity DESC LIMIT 50;
                        """
                    )
                    recent = cur.fetchall()
                    critical = [r for r in recent if (r["severity"] or 0) > 0.9]
                    warning = [r for r in recent if 0.5 < (r["severity"] or 0) <= 0.9]
                    low = [r for r in recent if (r["severity"] or 0) <= 0.5]
                    cells_affected = list({r["cell_id"] for r in critical if r["cell_id"]})

                    # Cross-reference with correlation data for root cause
                    cur.execute(
                        """
                        SELECT metric_x, metric_y, corr_value, method
                        FROM correlation_insights
                        WHERE ABS(corr_value) >= 0.7
                        ORDER BY created_at DESC LIMIT 10;
                        """
                    )
                    strong_corr = cur.fetchall()

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
                            "step": "Cross-reference correlations for root cause",
                            "strong_correlations": [
                                {
                                    "pair": f"{c['metric_x']} ↔ {c['metric_y']}",
                                    "value": float(c["corr_value"]),
                                    "method": c["method"],
                                }
                                for c in strong_corr
                            ],
                        },
                        {"step": "Triage complete", "priority": "P1" if critical else "P2"},
                    ]

                # ── pb-revenue-protect ────────────────────────────────────
                elif playbook_id == "pb-revenue-protect":
                    cur.execute(
                        """
                        SELECT subscriber_id, operator, severity, value, baseline_value, plan, line_type
                        FROM revenue_anomalies
                        WHERE severity > 0.8 AND created_at >= NOW() - INTERVAL '30 minutes'
                        ORDER BY severity DESC LIMIT 20;
                        """
                    )
                    flagged = cur.fetchall()
                    execution_log["steps"] = [
                        {"step": "Query high-severity revenue anomalies", "count": len(flagged)},
                        {
                            "step": "Flag suspicious subscribers",
                            "subscribers": [
                                {
                                    "id": r["subscriber_id"],
                                    "operator": r["operator"],
                                    "severity": float(r["severity"]),
                                    "revenue": float(r["value"]),
                                    "baseline": float(r["baseline_value"]),
                                    "plan": r["plan"],
                                }
                                for r in flagged
                            ],
                        },
                        {
                            "step": "Protection summary",
                            "flagged_count": len(flagged),
                            "total_revenue_at_risk": round(
                                sum(float(r["value"]) for r in flagged), 2
                            ),
                        },
                    ]

                # ── pb-sla-breach ─────────────────────────────────────────
                elif playbook_id == "pb-sla-breach":
                    cur.execute(
                        """
                        SELECT score, explanation, created_at
                        FROM sla_risk_scores
                        ORDER BY created_at DESC LIMIT 1;
                        """
                    )
                    sla = cur.fetchone()
                    if sla and sla.get("explanation"):
                        features = sla["explanation"].get("input_features", {})
                        top_driver = sla["explanation"].get("top_driver", "unknown")
                        # Identify KPIs exceeding thresholds
                        thresholds = {
                            "mean_latency_ms": 40.0,
                            "mean_packet_loss_pct": 1.0,
                            "mean_throughput_mbps": 50.0,  # below this is bad
                        }
                        breaching = []
                        for kpi, threshold in thresholds.items():
                            val = features.get(kpi)
                            if val is not None:
                                if kpi == "mean_throughput_mbps":
                                    if float(val) < threshold:
                                        breaching.append(
                                            {"kpi": kpi, "value": float(val), "threshold": threshold, "direction": "below"}
                                        )
                                elif float(val) > threshold:
                                    breaching.append(
                                        {"kpi": kpi, "value": float(val), "threshold": threshold, "direction": "above"}
                                    )
                        execution_log["steps"] = [
                            {"step": "Read current SLA score", "score": float(sla["score"])},
                            {"step": "Extract KPI features from model", "features": {k: float(v) for k, v in features.items()}},
                            {"step": "Identify top risk driver", "driver": top_driver},
                            {"step": "Check KPI thresholds", "breaching_kpis": breaching},
                            {"step": "Mitigation logged", "action": f"Focus remediation on {top_driver}"},
                        ]
                    else:
                        execution_log["steps"] = [{"step": "No SLA data available"}]

                # ── pb-capacity-scale ─────────────────────────────────────
                elif playbook_id == "pb-capacity-scale":
                    cur.execute(
                        """
                        SELECT
                            CAST(explanation->'input_features'->>'mean_throughput_mbps' AS DOUBLE PRECISION) AS throughput,
                            CAST(explanation->'input_features'->>'mean_active_users' AS DOUBLE PRECISION) AS users,
                            CAST(explanation->'input_features'->>'mean_latency_ms' AS DOUBLE PRECISION) AS latency,
                            created_at
                        FROM sla_risk_scores
                        WHERE explanation->'input_features' IS NOT NULL
                        ORDER BY created_at DESC LIMIT 10;
                        """
                    )
                    history = cur.fetchall()
                    if history:
                        avg_throughput = sum(r["throughput"] for r in history) / len(history)
                        avg_users = sum(r["users"] for r in history) / len(history)
                        avg_latency = sum(r["latency"] for r in history) / len(history)
                        max_throughput = max(r["throughput"] for r in history)
                        max_users = max(r["users"] for r in history)
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
