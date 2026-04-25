from fastapi import APIRouter, HTTPException, Query, Depends
from psycopg2.extras import RealDictCursor
from db import _db
from auth import require_auth

router = APIRouter()


@router.get("/anomalies")
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


@router.get("/revenue-anomalies")
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


@router.get("/anomaly-stats")
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
