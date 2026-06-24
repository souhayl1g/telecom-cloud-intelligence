from fastapi import APIRouter, HTTPException, Query, Depends
from psycopg2.extras import RealDictCursor
from db import _db
from auth import require_auth

router = APIRouter()


@router.get("/subscribers/{imsi_hash}")
def get_subscriber(
    imsi_hash: str,
    month_year: str = Query(default="2026-03"),
    user=Depends(require_auth),
):
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT s.*, f.rat_gap_score, f.usim_bottleneck, f.cem_score,
                       f.network_experience_index, f.churn_risk_flag
                FROM bss_subscribers s
                LEFT JOIN subscriber_features f ON s.imsi_hash = f.imsi_hash AND s.month_year = f.month_year
                WHERE s.imsi_hash = %s AND s.month_year = %s
                LIMIT 1
            """,
                (imsi_hash, month_year),
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return dict(row)


@router.get("/areas/{area}/cem")
def get_area_cem(
    area: str, month_year: str = Query(default="2026-03"), user=Depends(require_auth)
):
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM area_network_health
                WHERE area = %s AND month_year = %s
            """,
                (area, month_year),
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Area not found")
    return dict(row)


@router.get("/areas")
def list_areas(month_year: str = Query(default="2026-03"), user=Depends(require_auth)):
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT area, subscriber_count, avg_cem_score, underserved_pct,
                       usim_bottleneck_pct, anomaly_count
                FROM area_network_health
                WHERE month_year = %s
                ORDER BY avg_cem_score ASC
            """,
                (month_year,),
            )
            rows = cur.fetchall()
    return {"areas": [dict(r) for r in rows], "month_year": month_year}


@router.get("/conversations/{thread_id}")
def get_conversation(thread_id: str, user=Depends(require_auth)):
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM agent_conversations
                WHERE thread_id = %s
            """,
                (thread_id,),
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return dict(row)
