from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from jose import jwt, JWTError
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Telecom Cloud Intelligence — API Gateway", version="2.0")

Instrumentator().instrument(app).expose(app)

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
