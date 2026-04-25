from fastapi import APIRouter, HTTPException, Query, Depends
from psycopg2.extras import RealDictCursor
from db import _db
from auth import require_auth

router = APIRouter()


@router.get("/correlation")
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
