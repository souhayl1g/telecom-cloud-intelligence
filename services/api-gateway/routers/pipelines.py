from fastapi import APIRouter, HTTPException, Query, Depends
from psycopg2.extras import RealDictCursor
from db import _db
from auth import require_auth

router = APIRouter()


@router.get("/pipeline-runs")
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


@router.get("/kpi-summary")
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
