from fastapi import FastAPI, HTTPException, Query
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Telecom Cloud Intelligence — API Gateway", version="2.0")


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(db_url)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sla-risk")
def sla_risk_latest():
    try:
        with get_conn() as conn:
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
                    raise HTTPException(status_code=404, detail="No SLA risk scores found")
                return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sla-risk/history")
def sla_risk_history(limit: int = Query(default=20, ge=1, le=200)):
    """Return the last N SLA risk scores, newest first."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, run_id, region, score, model_version, created_at
                    FROM sla_risk_scores
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (limit,))
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/anomalies")
def anomalies_latest(limit: int = Query(default=50, ge=1, le=500)):
    """Return the N most recent detected anomalies, newest first."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, run_id, ts, region, cell_id, kpi_name,
                           severity, value, baseline_value, model_version, created_at
                    FROM anomalies
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (limit,))
                rows = cur.fetchall()
                return {"count": len(rows), "anomalies": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pipeline-runs")
def pipeline_runs(limit: int = Query(default=10, ge=1, le=100)):
    """Return the N most recent pipeline runs."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT run_id, status, started_at, finished_at, error_message
                    FROM pipeline_runs
                    ORDER BY id DESC
                    LIMIT %s;
                """, (limit,))
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/revenue-anomalies")
def revenue_anomalies_latest(limit: int = Query(default=50, ge=1, le=500)):
    """Return the N most recent detected BSS revenue anomalies."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, run_id, ts, region, operator, subscriber_id,
                           line_type, plan,
                           metric_name, severity, value, baseline_value,
                           model_version, created_at
                    FROM revenue_anomalies
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (limit,))
                rows = cur.fetchall()
                return {"count": len(rows), "revenue_anomalies": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/correlation")
def correlation_latest(limit: int = Query(default=50, ge=1, le=200)):
    """Return the N most recent OSS-BSS correlation insights."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, run_id, region, metric_x, metric_y,
                           window_start, window_end, method,
                           corr_value, p_value, created_at
                    FROM correlation_insights
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (limit,))
                rows = cur.fetchall()
                return {"count": len(rows), "correlations": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

