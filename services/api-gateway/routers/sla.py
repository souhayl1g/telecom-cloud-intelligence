from fastapi import APIRouter, HTTPException, Query, Depends
from psycopg2.extras import RealDictCursor
from db import _db
from auth import require_auth

router = APIRouter()


@router.get("/sla-risk")
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


@router.get("/sla-risk/history")
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
