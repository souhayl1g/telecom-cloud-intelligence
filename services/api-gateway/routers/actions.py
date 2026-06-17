import os
import uuid

from fastapi import APIRouter, HTTPException, Query, Depends, Body
from psycopg2.extras import RealDictCursor, Json
import requests
from db import _db
from auth import require_auth
from config import AI_SERVICE_URL, INTERNAL_API_KEY
from services import notifier, ticketing, pdf_report, storage

RETRAIN_SERVICE_URL = os.getenv("RETRAIN_SERVICE_URL", "http://retrain-service:8004")
RETRAIN_TIMEOUT = int(os.getenv("RETRAIN_TIMEOUT_SECONDS", "1800"))
REPORT_RECIPIENT_EMAIL = os.getenv("REPORT_RECIPIENT_EMAIL", "").strip()
DEMO_SMS_RECIPIENT = os.getenv("DEMO_SMS_RECIPIENT", "").strip()
REPORTS_BUCKET = os.getenv("REPORTS_BUCKET", "reports")


def _model_name_from_action(action: dict) -> str:
    """Pull model_name from action.execution_log.params or default to 'cem'."""
    el = action.get("execution_log") or {}
    if isinstance(el, dict):
        params = el.get("params") or {}
        m = params.get("model_name")
        if m in ("cem", "rat", "vae"):
            return m
    desc = (action.get("description") or "").lower()
    if "vae" in desc or "anomaly" in desc:
        return "vae"
    if "rat" in desc or "underservice" in desc:
        return "rat"
    return "cem"


def _action_metadata(action: dict) -> dict:
    """Best-effort extraction of metadata payload attached to the action."""
    el = action.get("execution_log") or {}
    if isinstance(el, dict):
        meta = el.get("metadata") or el.get("params") or {}
        if isinstance(meta, dict):
            return meta
    return {}

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

                if action.get("status") in ("executed",):
                    raise HTTPException(status_code=409, detail="Action has already been executed")

                playbook_id = action.get("playbook_id")
                execution_log = {"playbook_id": playbook_id, "steps": []}

                # ── pb-model-retrain ──────────────────────────────────────
                if playbook_id == "pb-model-retrain":
                    try:
                        r = requests.post(
                            f"{AI_SERVICE_URL}/models/reload", timeout=15, headers={"X-Internal-Key": INTERNAL_API_KEY}
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

                # ── pb-alert-subscriber ───────────────────────────────────
                elif playbook_id == "pb-alert-subscriber":
                    meta = _action_metadata(action)
                    target_imsi = meta.get("imsi_hash")
                    target_phone = meta.get("phone") or DEMO_SMS_RECIPIENT or None
                    target_email = meta.get("email") or REPORT_RECIPIENT_EMAIL or None

                    # If no explicit target, pick top-N most at-risk subscribers
                    recipients: list[dict] = []
                    if target_imsi:
                        cur.execute(
                            """SELECT imsi_hash, cem_score, rat_gap_score, features_json
                                 FROM subscriber_features
                                WHERE imsi_hash = %s
                                ORDER BY created_at DESC LIMIT 1;""",
                            (target_imsi,),
                        )
                        r = cur.fetchone()
                        if r:
                            recipients.append(dict(r))
                    else:
                        cur.execute(
                            """SELECT imsi_hash, cem_score, rat_gap_score, features_json
                                 FROM subscriber_features
                                WHERE cem_score < 0.3 OR rat_gap_score > 0.5
                                ORDER BY cem_score ASC NULLS LAST LIMIT 10;"""
                        )
                        recipients = [dict(r) for r in cur.fetchall()]

                    body_template = (
                        meta.get("message")
                        or "Tunisie Telecom: we detected service-quality issues in your area. "
                           "Our team is actively optimizing your network. Expected resolution: 48h."
                    )

                    send_results = []
                    for rec in recipients:
                        rcp = (
                            target_phone
                            or (rec.get("features_json") or {}).get("phone")
                            or rec["imsi_hash"]  # falls back to imsi as identifier in console mode
                        )
                        nr = notifier.send_sms(
                            rcp,
                            body_template,
                            source_action_id=action_id,
                            source_imsi_hash=rec["imsi_hash"],
                        )
                        send_results.append(nr.dict())
                        if target_email:
                            er = notifier.send_email(
                                target_email,
                                "[NeXo] Network optimization in progress",
                                body_template,
                                source_action_id=action_id,
                            )
                            send_results.append(er.dict())

                    execution_log["steps"] = [
                        {"step": "Resolve recipients", "count": len(recipients)},
                        {"step": "Send notifications", "results": send_results},
                        {
                            "step": "Summary",
                            "sent": sum(1 for r in send_results if r["status"] == "sent"),
                            "logged": sum(1 for r in send_results if r["status"] == "logged"),
                            "failed": sum(1 for r in send_results if r["status"] == "failed"),
                        },
                    ]

                # ── pb-create-ticket ──────────────────────────────────────
                elif playbook_id == "pb-create-ticket":
                    meta = _action_metadata(action)
                    severity = action.get("severity") or meta.get("severity") or "warning"
                    ticket = ticketing.create_ticket(
                        title=action.get("title") or "L4 Agent Ticket",
                        description=action.get("description"),
                        severity=severity,
                        source_action_id=action_id,
                        cell_id=meta.get("cell_id"),
                        area=meta.get("area"),
                        metadata={
                            "anomaly_id": meta.get("anomaly_id"),
                            "kpis": meta.get("kpis"),
                            "source": action.get("source"),
                            "confidence": float(action.get("confidence") or 0),
                        },
                    )

                    # Critical → also notify on-call (console-log unless SMTP set)
                    notif_results = []
                    if severity == "critical":
                        oncall_email = os.getenv("ONCALL_EMAIL", "noc-oncall@tunisietelecom.tn")
                        er = notifier.send_email(
                            oncall_email,
                            f"[NeXo CRITICAL] {ticket['ticket_id']} - {action.get('title')}",
                            f"Ticket {ticket['ticket_id']} opened. Severity: critical.\n\n"
                            f"{action.get('description') or ''}\n\nReview at /tickets/{ticket['ticket_id']}",
                            source_action_id=action_id,
                        )
                        notif_results.append(er.dict())

                    execution_log["steps"] = [
                        {"step": "Create ticket", "ticket_id": ticket["ticket_id"]},
                        {"step": "Severity", "value": severity},
                        {"step": "Notifications", "results": notif_results},
                    ]

                # ── pb-retrain-model (real) ───────────────────────────────
                elif playbook_id == "pb-retrain-model":
                    model_name = _model_name_from_action(action)
                    run_id = f"retrain-{uuid.uuid4().hex[:12]}"

                    # Snapshot metrics_before (placeholder — real metrics come from
                    # /model-metrics if available)
                    metrics_before: dict = {}
                    try:
                        mr = requests.get(
                            "http://dashboard:3001/api/model-metrics", timeout=5
                        )
                        if mr.ok:
                            metrics_before = mr.json()
                    except Exception:
                        pass

                    # Register start
                    cur.execute(
                        """INSERT INTO retrain_runs
                              (run_id, model_name, notebook_path, status,
                               metrics_before, source_action_id)
                           VALUES (%s, %s, %s, 'started', %s, %s);""",
                        (
                            run_id,
                            model_name,
                            f"notebooks/{ {'cem':'02_cem_score_training.ipynb', 'rat':'04_rat_underservice_training.ipynb', 'vae':'03_oss_vae_anomaly_training.ipynb'}[model_name] }",
                            Json(metrics_before),
                            action_id,
                        ),
                    )

                    # Call retrain-service
                    retrain_payload = {
                        "model_name": model_name,
                        "run_id": run_id,
                        "params": _action_metadata(action).get("params", {}),
                    }
                    retrain_result: dict
                    try:
                        rr = requests.post(
                            f"{RETRAIN_SERVICE_URL}/retrain",
                            json=retrain_payload,
                            timeout=RETRAIN_TIMEOUT,
                            headers={"X-Internal-Key": INTERNAL_API_KEY},
                        )
                        rr.raise_for_status()
                        retrain_result = rr.json()
                        status_out = retrain_result.get("status", "succeeded")
                    except Exception as e:
                        retrain_result = {"error": str(e)[:300]}
                        status_out = "failed"

                    # Reload models in ai-service if retrain succeeded
                    reload_result: dict = {}
                    metrics_dump_result: dict = {}
                    if status_out == "succeeded":
                        try:
                            r = requests.post(
                                f"{AI_SERVICE_URL}/models/reload", timeout=30, headers={"X-Internal-Key": INTERNAL_API_KEY}
                            )
                            r.raise_for_status()
                            reload_result = r.json()
                        except Exception as e:
                            reload_result = {"error": str(e)[:300]}

                        # Refresh notebooks/models/metrics.json so the
                        # dashboard /api/model-metrics route serves the new
                        # honest numbers without a redeploy.
                        try:
                            import subprocess
                            proc = subprocess.run(
                                ["python3", "/scripts/dump_model_metrics.py"],
                                capture_output=True, text=True, timeout=30,
                            )
                            metrics_dump_result = {
                                "exit_code": proc.returncode,
                                "stdout_tail": (proc.stdout or "")[-400:],
                                "stderr_tail": (proc.stderr or "")[-400:],
                            }
                        except Exception as e:
                            metrics_dump_result = {"error": str(e)[:300]}

                    # Update retrain_runs
                    cur.execute(
                        """UPDATE retrain_runs
                              SET status = %s, finished_at = now(),
                                  output_path = %s,
                                  metrics_after = %s,
                                  error = %s
                            WHERE run_id = %s;""",
                        (
                            status_out,
                            retrain_result.get("executed_notebook_minio_key"),
                            Json(retrain_result.get("metrics") or {}),
                            retrain_result.get("error"),
                            run_id,
                        ),
                    )

                    execution_log["steps"] = [
                        {"step": "Resolve model", "model_name": model_name},
                        {"step": "Snapshot metrics_before", "metrics": metrics_before},
                        {"step": "Run training notebook", "result": retrain_result},
                        {"step": "Hot-reload models in ai-service", "result": reload_result},
                        {"step": "Persist retrain_runs row", "run_id": run_id, "status": status_out},
                    ]

                # ── pb-capacity-report ────────────────────────────────────
                elif playbook_id == "pb-capacity-report":
                    meta = _action_metadata(action)
                    area = meta.get("area", "ALL")
                    email_to = (meta.get("email_to") or REPORT_RECIPIENT_EMAIL or "").strip()
                    try:
                        report = pdf_report.generate_capacity_report(
                            area=area, source_action_id=action_id
                        )
                        steps = [
                            {"step": "Pull KPI history + anomalies", "area": area},
                            {"step": "Render PDF (fpdf2)"},
                            {"step": "Upload to MinIO", "minio_key": report.get("minio_key")},
                            {
                                "step": "Capacity report ready",
                                "report_id": report.get("report_id"),
                                "presigned_url": report.get("presigned_url"),
                                "url_expires_at": report.get("url_expires_at"),
                                "metrics_summary": report.get("metrics_summary"),
                            },
                        ]

                        # Email the PDF if a recipient is configured + upload succeeded.
                        if email_to and report.get("minio_key"):
                            try:
                                pdf_bytes = storage.download_bytes(
                                    bucket=REPORTS_BUCKET, key=report["minio_key"]
                                )
                                ms = report.get("metrics_summary") or {}
                                recs = ms.get("recommendations") or []
                                rec_lines = "\n".join(f"  - {r}" for r in recs) if recs else "  (none)"
                                per_rat_lines = "\n".join(
                                    f"  - {rt.get('rat_type')}: {rt.get('row_count', 0):,} rows, "
                                    f"{rt.get('anomaly_count', 0):,} anomalies, "
                                    f"integrity={rt.get('avg_integrity_pct', '—')}%, "
                                    f"CDR={rt.get('avg_cdr_pct', '—')}%"
                                    for rt in (ms.get("per_rat") or [])
                                ) or "  (no per-RAT breakdown)"
                                body = (
                                    f"NeXo Capacity Recommendation Report (Real Huawei OSS data)\n"
                                    f"Area: {area}\n"
                                    f"Report ID: {report.get('report_id')}\n"
                                    f"Hourly buckets analyzed: {ms.get('cycles_analyzed', 0)}\n"
                                    f"Total cell-rows: {ms.get('total_rows', 0):,}\n"
                                    f"Avg call integrity: {ms.get('avg_integrity_pct', '—')}%\n"
                                    f"Avg call drop rate: {ms.get('avg_call_drop_rate_pct', '—')}%\n"
                                    f"Avg throughput (3G+4G): {ms.get('avg_throughput_mbps', '—')} Mbps\n"
                                    f"Avg 4G RSRP: {ms.get('avg_rsrp_dbm', '—')} dBm\n"
                                    f"Total anomalies: {ms.get('anomaly_count', 0):,}\n\n"
                                    f"Per-RAT breakdown:\n{per_rat_lines}\n\n"
                                    f"Recommendations:\n{rec_lines}\n\n"
                                    f"Note: latency / packet loss / jitter / cell load are not in the "
                                    f"Huawei source CSV and are intentionally omitted from this report.\n\n"
                                    f"Download link (expires in 7 days):\n{report.get('presigned_url')}\n\n"
                                    f"-- NeXo ADN L4 Operations Agent"
                                )
                                pdf_filename = f"{report.get('report_id')}.pdf"
                                nr = notifier.send_email_with_attachment(
                                    email_to,
                                    f"[NeXo] Capacity Report — {area} — {report.get('report_id')}",
                                    body,
                                    pdf_bytes,
                                    pdf_filename,
                                    source_action_id=action_id,
                                )
                                steps.append({
                                    "step": "Email PDF",
                                    "to": email_to,
                                    "provider": nr.provider,
                                    "status": nr.status,
                                    "provider_msg_id": nr.provider_msg_id,
                                    "error": nr.error,
                                })
                            except Exception as mail_err:
                                steps.append({
                                    "step": "Email PDF",
                                    "error": str(mail_err)[:300],
                                })

                        execution_log["steps"] = steps
                    except Exception as e:
                        execution_log["steps"] = [{"step": "Generate PDF", "error": str(e)[:300]}]

                # ── pb-cem-degradation ────────────────────────────────────
                elif playbook_id == "pb-cem-degradation":
                    # 1. Find areas with poor average CEM scores
                    cur.execute(
                        """
                        SELECT area, avg_cem_score, underserved_pct, subscriber_count, anomaly_count
                        FROM area_network_health
                        WHERE avg_cem_score < 0.3 OR underserved_pct > 15
                        ORDER BY avg_cem_score ASC NULLS LAST
                        LIMIT 10;
                        """
                    )
                    poor_areas = [dict(r) for r in cur.fetchall()]
                    worst_area = poor_areas[0] if poor_areas else None

                    # 2. Cross-reference OSS KPI anomalies in those areas
                    oss_anomalies = []
                    if poor_areas:
                        area_list = [a["area"] for a in poor_areas if a["area"]]
                        if area_list:
                            cur.execute(
                                """
                                SELECT cell_id, area, rat_type, cell_load_pct, latency_ms,
                                       packet_loss_rate, call_drop_rate, rsrp_dbm
                                FROM oss_cell_kpis
                                WHERE area = ANY(%s)
                                  AND (anomaly_flag = TRUE OR cell_load_pct > 80
                                       OR packet_loss_rate > 0.05 OR call_drop_rate > 0.03)
                                ORDER BY cell_load_pct DESC NULLS LAST
                                LIMIT 20;
                                """,
                                (area_list,),
                            )
                            oss_anomalies = [dict(r) for r in cur.fetchall()]

                    # 3. Cross-reference VAE anomaly scores in those areas
                    vae_anomalies = []
                    if poor_areas:
                        area_list = [a["area"] for a in poor_areas if a["area"]]
                        if area_list:
                            cur.execute(
                                """
                                SELECT region, cell_id, anomaly_score, reconstruction_error
                                FROM vae_anomaly_scores
                                WHERE region = ANY(%s)
                                  AND is_anomaly = TRUE
                                ORDER BY anomaly_score DESC NULLS LAST
                                LIMIT 20;
                                """,
                                (area_list,),
                            )
                            vae_anomalies = [dict(r) for r in cur.fetchall()]

                    # 4. Identify root-cause KPIs from OSS anomalies
                    root_causes = []
                    for oa in oss_anomalies[:5]:
                        causes = []
                        if (oa.get("cell_load_pct") or 0) > 80:
                            causes.append("high_cell_load")
                        if (oa.get("latency_ms") or 0) > 100:
                            causes.append("high_latency")
                        if (oa.get("packet_loss_rate") or 0) > 0.05:
                            causes.append("packet_loss")
                        if (oa.get("call_drop_rate") or 0) > 0.03:
                            causes.append("call_drops")
                        if (oa.get("rsrp_dbm") or 0) < -110:
                            causes.append("poor_coverage")
                        if causes:
                            root_causes.append({
                                "cell_id": oa["cell_id"],
                                "area": oa["area"],
                                "causes": causes,
                            })

                    # 5. Create ticket for worst affected area
                    ticket = None
                    if worst_area:
                        ticket = ticketing.create_ticket(
                            title=f"CEM Degradation: {worst_area['area']} — poor subscriber experience",
                            description=(
                                f"Area {worst_area['area']} shows degraded CEM metrics:\n"
                                f"- Average CEM score: {worst_area.get('avg_cem_score', '—')}\n"
                                f"- Underserved subscribers: {worst_area.get('underserved_pct', '—')}%\n"
                                f"- OSS anomalies detected: {len(oss_anomalies)}\n"
                                f"- VAE anomalies detected: {len(vae_anomalies)}"
                            ),
                            severity="critical" if (worst_area.get("avg_cem_score") or 1) < 0.2 else "warning",
                            source_action_id=action_id,
                            area=worst_area["area"],
                            metadata={
                                "poor_areas_count": len(poor_areas),
                                "oss_anomaly_count": len(oss_anomalies),
                                "vae_anomaly_count": len(vae_anomalies),
                                "root_causes": root_causes[:5],
                            },
                        )

                    # 6. Send alert notification
                    notif_result = None
                    if worst_area:
                        notif_result = notifier.send_alert(
                            subject=f"[NeXo] CEM Degradation in {worst_area['area']}",
                            body=(
                                f"Area {worst_area['area']} has poor CEM scores. "
                                f"Ticket {ticket['ticket_id'] if ticket else 'N/A'} opened. "
                                f"OSS anomalies: {len(oss_anomalies)}, VAE anomalies: {len(vae_anomalies)}."
                            ),
                            source_action_id=action_id,
                        )

                    execution_log["steps"] = [
                        {"step": "Identify poor CEM areas", "count": len(poor_areas), "areas": [a["area"] for a in poor_areas]},
                        {"step": "Correlate OSS anomalies", "count": len(oss_anomalies), "top_cells": [a["cell_id"] for a in oss_anomalies[:5]]},
                        {"step": "Correlate VAE anomalies", "count": len(vae_anomalies)},
                        {"step": "Root-cause KPIs", "top_causes": root_causes[:5]},
                        {"step": "Create NOC ticket", "ticket_id": ticket["ticket_id"] if ticket else None},
                        {"step": "Send alert", "status": notif_result.status if notif_result else None},
                        {
                            "step": "Summary",
                            "worst_area": worst_area["area"] if worst_area else None,
                            "avg_cem_score": float(worst_area["avg_cem_score"]) if worst_area and worst_area.get("avg_cem_score") else None,
                        },
                    ]

                # ── pb-churn-prevention (workflow) ────────────────────────
                elif playbook_id == "pb-churn-prevention":
                    meta = _action_metadata(action)
                    limit = int(meta.get("limit", 100))

                    cur.execute(
                        """SELECT imsi_hash, cem_score, rat_gap_score,
                                  usim_bottleneck, features_json
                             FROM subscriber_features
                            WHERE COALESCE(rat_gap_score, 0) > 0.5
                              AND COALESCE(cem_score, 1) < 0.3
                            ORDER BY cem_score ASC NULLS LAST
                            LIMIT %s;""",
                        (limit,),
                    )
                    high_risk = [dict(r) for r in cur.fetchall()]

                    sms_count = 0
                    sim_offer_count = 0
                    intervention_rows = []
                    body_template = (
                        "Tunisie Telecom: we have a special offer to improve your service. "
                        "Reply YES for a free 5GB data bonus or call *100# to discuss your plan."
                    )

                    for sub in high_risk:
                        intervention_type = "sms_offer"
                        if sub.get("usim_bottleneck"):
                            intervention_type = "sim_upgrade_offer"
                            body_sub = (
                                "Tunisie Telecom: your 4G device is limited by an old SIM. "
                                "Visit any TT store for a FREE SIM upgrade to unlock 4G speeds."
                            )
                        else:
                            body_sub = body_template

                        rcp = (sub.get("features_json") or {}).get("phone") or DEMO_SMS_RECIPIENT or sub["imsi_hash"]
                        nr = notifier.send_sms(
                            rcp,
                            body_sub,
                            source_action_id=action_id,
                            source_imsi_hash=sub["imsi_hash"],
                        )
                        if nr.status in ("sent", "logged"):
                            sms_count += 1
                        if intervention_type == "sim_upgrade_offer":
                            sim_offer_count += 1

                        intervention_id = f"int-{uuid.uuid4().hex[:12]}"
                        cur.execute(
                            """INSERT INTO churn_interventions
                                  (intervention_id, imsi_hash, intervention_type,
                                   cem_at_intervention, rat_gap_at_intervention,
                                   intervention_payload, source_action_id, outcome)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending');""",
                            (
                                intervention_id,
                                sub["imsi_hash"],
                                intervention_type,
                                sub.get("cem_score"),
                                sub.get("rat_gap_score"),
                                Json({
                                    "channel": "sms",
                                    "message": body_sub,
                                    "provider": nr.provider,
                                    "provider_msg_id": nr.provider_msg_id,
                                }),
                                action_id,
                            ),
                        )
                        intervention_rows.append(intervention_id)

                    # Bulk batch above threshold also creates a tracking ticket
                    bulk_ticket = None
                    if len(high_risk) >= 20:
                        bulk_ticket = ticketing.create_ticket(
                            title=f"Bulk churn-risk batch: {len(high_risk)} subscribers",
                            description=(
                                f"Auto-generated by pb-churn-prevention. "
                                f"{sim_offer_count} subscribers offered SIM upgrade. "
                                f"{sms_count} retention SMS dispatched."
                            ),
                            severity="warning",
                            source_action_id=action_id,
                            area=None,
                            metadata={
                                "interventions_count": len(intervention_rows),
                                "first_interventions": intervention_rows[:10],
                            },
                        )

                    # Estimated revenue protected (rough heuristic — 20 TND/month/subscriber)
                    est_revenue_protected = len(high_risk) * 20

                    execution_log["steps"] = [
                        {"step": "Query high-risk subscribers", "count": len(high_risk)},
                        {"step": "Dispatch retention SMS", "sent": sms_count},
                        {"step": "SIM upgrade offers", "count": sim_offer_count},
                        {"step": "Create interventions", "count": len(intervention_rows)},
                        {
                            "step": "Open bulk tracking ticket",
                            "ticket_id": bulk_ticket["ticket_id"] if bulk_ticket else None,
                        },
                        {
                            "step": "Outcome tracking armed",
                            "follow_up_in_minutes": 120,
                            "estimated_revenue_protected_tnd_per_month": est_revenue_protected,
                        },
                    ]

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
