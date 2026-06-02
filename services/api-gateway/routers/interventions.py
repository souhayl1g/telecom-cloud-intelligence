"""REST endpoints for churn intervention outcomes (longitudinal tracking)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from auth import require_auth
from db import _db

router = APIRouter()


@router.get("/interventions")
def list_interventions(
    imsi_hash: str = Query(default=None),
    outcome: str = Query(default=None),
    intervention_type: str = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    user=Depends(require_auth),
):
    where = []
    params: list = []
    if imsi_hash:
        where.append("imsi_hash = %s")
        params.append(imsi_hash)
    if outcome:
        where.append("outcome = %s")
        params.append(outcome)
    if intervention_type:
        where.append("intervention_type = %s")
        params.append(intervention_type)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT * FROM churn_interventions
                    {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    tuple(params),
                )
                rows = list(cur.fetchall())
        return {"interventions": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interventions/stats")
def intervention_stats(user=Depends(require_auth)):
    """Outcome distribution + CEM delta aggregates for dashboard."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*)                                              AS total,
                      COUNT(*) FILTER (WHERE outcome = 'pending')           AS pending,
                      COUNT(*) FILTER (WHERE outcome = 'improved')          AS improved,
                      COUNT(*) FILTER (WHERE outcome = 'no_change')         AS no_change,
                      COUNT(*) FILTER (WHERE outcome = 'worsened')          AS worsened,
                      AVG(follow_up_cem - cem_at_intervention)
                        FILTER (WHERE follow_up_cem IS NOT NULL)             AS avg_cem_delta,
                      COUNT(*) FILTER (WHERE intervention_type = 'sms_offer')         AS sms_count,
                      COUNT(*) FILTER (WHERE intervention_type = 'sim_upgrade_offer') AS sim_count,
                      COUNT(*) FILTER (WHERE intervention_type = 'plan_upgrade')      AS plan_count,
                      COUNT(*) FILTER (WHERE intervention_type = 'ticket_created')    AS ticket_count
                    FROM churn_interventions;
                    """
                )
                row = cur.fetchone() or {}
                cur.execute(
                    """
                    SELECT date_trunc('day', created_at) AS day,
                           COUNT(*) AS count,
                           COUNT(*) FILTER (WHERE outcome = 'improved') AS improved
                    FROM churn_interventions
                    WHERE created_at >= now() - INTERVAL '14 days'
                    GROUP BY day
                    ORDER BY day;
                    """
                )
                row["daily"] = list(cur.fetchall())
        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
