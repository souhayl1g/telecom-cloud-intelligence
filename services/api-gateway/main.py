import os
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import requests
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from jose import jwt, JWTError
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _setup_tracing() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "api-gateway"),
        "service.version": "2.0",
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


_setup_tracing()

app = FastAPI(title="Telecom Cloud Intelligence — API Gateway", version="2.0")
FastAPIInstrumentor.instrument_app(app)

# ---------------------------------------------------------------------------
# JWT auth config
# ---------------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Decode and validate JWT token. Returns user payload or None if no token."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_auth(user=Depends(get_current_user)):
    """Dependency that requires a valid JWT token."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(db_url)


@contextmanager
def _db():
    """Open a psycopg2 connection, commit on success, rollback on error, always close."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public endpoints (no auth required)
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Protected endpoints (auth required)
# ---------------------------------------------------------------------------


@app.get("/sla-risk")
def sla_risk_latest(user=Depends(require_auth)):
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, run_id, region, window_start, window_end,
                           score, explanation, model_name, model_version, created_at
                    FROM sla_risk_scores
                    ORDER BY created_at DESC
                    LIMIT 1;
                """)
                row = cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=404, detail="No SLA risk scores found"
                    )
                return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sla-risk/history")
def sla_risk_history(
    limit: int = Query(default=20, ge=1, le=200), user=Depends(require_auth)
):
    """Return the last N SLA risk scores, newest first."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, run_id, region, score, model_version, created_at
                    FROM sla_risk_scores
                    ORDER BY created_at DESC
                    LIMIT %s;
                """,
                    (limit,),
                )
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/anomalies")
def anomalies_latest(
    limit: int = Query(default=50, ge=1, le=500), user=Depends(require_auth)
):
    """Return the N most recent detected anomalies, newest first."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, run_id, ts, region, cell_id, kpi_name,
                           severity, value, baseline_value, model_version, created_at
                    FROM anomalies
                    ORDER BY created_at DESC
                    LIMIT %s;
                """,
                    (limit,),
                )
                rows = cur.fetchall()
                return {"count": len(rows), "anomalies": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pipeline-runs")
def pipeline_runs(
    limit: int = Query(default=10, ge=1, le=100), user=Depends(require_auth)
):
    """Return the N most recent pipeline runs."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT run_id, status, started_at, finished_at, error_message
                    FROM pipeline_runs
                    ORDER BY id DESC
                    LIMIT %s;
                """,
                    (limit,),
                )
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/revenue-anomalies")
def revenue_anomalies_latest(
    limit: int = Query(default=50, ge=1, le=500), user=Depends(require_auth)
):
    """Return the N most recent detected BSS revenue anomalies."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, run_id, ts, region, operator, subscriber_id,
                           line_type, plan,
                           metric_name, severity, value, baseline_value,
                           model_version, created_at
                    FROM revenue_anomalies
                    ORDER BY created_at DESC
                    LIMIT %s;
                """,
                    (limit,),
                )
                rows = cur.fetchall()
                return {"count": len(rows), "revenue_anomalies": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/correlation")
def correlation_latest(
    limit: int = Query(default=50, ge=1, le=200), user=Depends(require_auth)
):
    """Return the N most recent OSS-BSS correlation insights."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, run_id, region, metric_x, metric_y,
                           window_start, window_end, method,
                           corr_value, p_value, created_at
                    FROM correlation_insights
                    ORDER BY created_at DESC
                    LIMIT %s;
                """,
                    (limit,),
                )
                rows = cur.fetchall()
                return {"count": len(rows), "correlations": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/platform-stats")
def platform_stats(user=Depends(require_auth)):
    """Return aggregated platform statistics for capacity planning and topology."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Pipeline run counts
                cur.execute("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE status='succeeded') AS succeeded FROM pipeline_runs;")
                run_stats = cur.fetchone()

                # Anomaly counts by severity
                cur.execute("""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE severity > 0.9) AS critical,
                        COUNT(*) FILTER (WHERE severity > 0.5 AND severity <= 0.9) AS warning,
                        COUNT(*) FILTER (WHERE severity <= 0.5) AS low,
                        AVG(severity) AS avg_severity
                    FROM anomalies
                    WHERE created_at >= NOW() - INTERVAL '1 hour';
                """)
                anomaly_stats = cur.fetchone()

                # Revenue anomaly stats
                cur.execute("""
                    SELECT COUNT(*) AS total, AVG(severity) AS avg_severity
                    FROM revenue_anomalies
                    WHERE created_at >= NOW() - INTERVAL '1 hour';
                """)
                revenue_stats = cur.fetchone()

                # Average KPIs from recent anomalies (proxy for current network state)
                cur.execute("""
                    SELECT
                        AVG(CAST(value AS FLOAT)) AS avg_kpi_value,
                        COUNT(DISTINCT cell_id) AS unique_cells,
                        COUNT(DISTINCT region) AS unique_regions
                    FROM anomalies
                    WHERE created_at >= NOW() - INTERVAL '1 hour';
                """)
                kpi_stats = cur.fetchone()

                # SLA risk trend (last 20)
                cur.execute("SELECT score, created_at FROM sla_risk_scores ORDER BY created_at DESC LIMIT 20;")
                sla_trend = cur.fetchall()

                return {
                    "pipeline": run_stats,
                    "anomalies": anomaly_stats,
                    "revenue_anomalies": revenue_stats,
                    "network": kpi_stats,
                    "sla_trend": sla_trend,
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Anomaly stats (per-run rates for forecast page)
# ---------------------------------------------------------------------------


@app.get("/anomaly-stats")
def anomaly_stats(
    limit: int = Query(default=20, ge=1, le=200), user=Depends(require_auth)
):
    """Return per-pipeline-run anomaly counts and average severity."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT pr.run_id, pr.started_at,
                           COUNT(DISTINCT a.id) AS oss_anomaly_count,
                           COUNT(DISTINCT ra.id) AS bss_anomaly_count,
                           COALESCE(AVG(a.severity), 0) AS avg_oss_severity,
                           COALESCE(AVG(ra.severity), 0) AS avg_bss_severity
                    FROM pipeline_runs pr
                    LEFT JOIN anomalies a ON a.run_id = pr.run_id
                    LEFT JOIN revenue_anomalies ra ON ra.run_id = pr.run_id
                    WHERE pr.status = 'succeeded'
                    GROUP BY pr.run_id, pr.started_at
                    ORDER BY pr.started_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# KPI summary (real aggregates from SLA model explanation for capacity page)
# ---------------------------------------------------------------------------


@app.get("/kpi-summary")
def kpi_summary(
    limit: int = Query(default=20, ge=1, le=200), user=Depends(require_auth)
):
    """Return real KPI aggregates extracted from SLA model explanation JSONB."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        score,
                        CAST(explanation->'input_features'->>'mean_throughput_mbps' AS DOUBLE PRECISION) AS avg_throughput,
                        CAST(explanation->'input_features'->>'mean_latency_ms' AS DOUBLE PRECISION) AS avg_latency,
                        CAST(explanation->'input_features'->>'mean_active_users' AS DOUBLE PRECISION) AS avg_users,
                        CAST(explanation->'input_features'->>'mean_packet_loss_pct' AS DOUBLE PRECISION) AS avg_packet_loss,
                        CAST(explanation->'input_features'->>'mean_signal_rsrp_dbm' AS DOUBLE PRECISION) AS avg_signal_rsrp,
                        created_at
                    FROM sla_risk_scores
                    WHERE explanation->'input_features' IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Infrastructure Stats (real DB + storage metrics for capacity page)
# ---------------------------------------------------------------------------


@app.get("/infra-stats")
def infra_stats(user=Depends(require_auth)):
    """Return real infrastructure metrics: row counts, DB size, pipeline timing."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Row counts per table
                cur.execute("""
                    SELECT
                        (SELECT count(*) FROM pipeline_runs) AS pipeline_runs,
                        (SELECT count(*) FROM anomalies) AS anomalies,
                        (SELECT count(*) FROM revenue_anomalies) AS revenue_anomalies,
                        (SELECT count(*) FROM sla_risk_scores) AS sla_scores,
                        (SELECT count(*) FROM correlation_insights) AS correlations,
                        (SELECT count(*) FROM dataset_registry) AS datasets,
                        (SELECT count(*) FROM agent_actions) AS actions,
                        (SELECT count(*) FROM users) AS users;
                """)
                row_counts = cur.fetchone()

                # Total data lake rows from dataset_registry
                cur.execute("SELECT COALESCE(SUM(row_count), 0) AS total_data_rows FROM dataset_registry;")
                data_rows = cur.fetchone()

                # Real DB size
                cur.execute("SELECT pg_database_size(current_database()) AS db_size_bytes;")
                db_size = cur.fetchone()

                # Real table sizes
                cur.execute("""
                    SELECT
                        pg_total_relation_size('anomalies') AS anomalies_bytes,
                        pg_total_relation_size('correlation_insights') AS correlations_bytes,
                        pg_total_relation_size('sla_risk_scores') AS sla_bytes,
                        pg_total_relation_size('revenue_anomalies') AS revenue_bytes,
                        pg_total_relation_size('dataset_registry') AS datasets_bytes,
                        pg_total_relation_size('pipeline_runs') AS pipeline_bytes;
                """)
                table_sizes = cur.fetchone()

                # Pipeline execution times
                cur.execute("""
                    SELECT
                        count(*) AS finished_runs,
                        COALESCE(AVG(EXTRACT(EPOCH FROM (finished_at - started_at))), 0) AS avg_duration_sec,
                        COALESCE(MAX(EXTRACT(EPOCH FROM (finished_at - started_at))), 0) AS max_duration_sec
                    FROM pipeline_runs
                    WHERE finished_at IS NOT NULL;
                """)
                pipeline_timing = cur.fetchone()

                # Dataset count per layer
                cur.execute("""
                    SELECT layer, count(*) AS count, COALESCE(SUM(row_count), 0) AS rows
                    FROM dataset_registry
                    GROUP BY layer ORDER BY layer;
                """)
                layers = cur.fetchall()

                total_rows = sum(int(v) for v in row_counts.values())

                return {
                    "row_counts": {k: int(v) for k, v in row_counts.items()},
                    "total_rows": total_rows,
                    "total_data_rows": int(data_rows["total_data_rows"]),
                    "db_size_bytes": int(db_size["db_size_bytes"]),
                    "db_size_mb": round(int(db_size["db_size_bytes"]) / (1024 * 1024), 1),
                    "table_sizes": {k: int(v) for k, v in table_sizes.items()},
                    "pipeline_timing": {
                        "finished_runs": int(pipeline_timing["finished_runs"]),
                        "avg_duration_sec": round(float(pipeline_timing["avg_duration_sec"]), 1),
                        "max_duration_sec": round(float(pipeline_timing["max_duration_sec"]), 1),
                    },
                    "data_lake_layers": [
                        {"layer": r["layer"], "datasets": int(r["count"]), "rows": int(r["rows"])}
                        for r in layers
                    ],
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Agent Actions (L4 autonomous operations — CRUD + playbook execution)
# ---------------------------------------------------------------------------

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8001")


@app.get("/actions")
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


@app.post("/actions")
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


@app.patch("/actions/{action_id}")
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


@app.post("/actions/{action_id}/execute")
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
