"""REST endpoints for notification audit + manual SMS/email triggers."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from auth import require_auth
from services import notifier

router = APIRouter()


@router.get("/notifications")
def list_notifications(
    recipient: str = Query(default=None),
    channel: str = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    user=Depends(require_auth),
):
    """Audit list of sent notifications."""
    try:
        rows = notifier.list_notifications(
            recipient=recipient, channel=channel, limit=limit
        )
        return {"notifications": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/sms")
def send_sms(body: dict = Body(...), user=Depends(require_auth)):
    """Trigger an ad-hoc SMS send (manual test or external workflow)."""
    recipient = body.get("recipient")
    text = body.get("body")
    if not recipient or not text:
        raise HTTPException(status_code=400, detail="recipient and body required")
    result = notifier.send_sms(
        recipient,
        text,
        source_action_id=body.get("source_action_id"),
        source_imsi_hash=body.get("source_imsi_hash"),
    )
    return result.dict()


@router.post("/notifications/email")
def send_email(body: dict = Body(...), user=Depends(require_auth)):
    """Trigger an ad-hoc email send."""
    recipient = body.get("recipient")
    subject = body.get("subject", "[NeXo] Notification")
    text = body.get("body")
    if not recipient or not text:
        raise HTTPException(status_code=400, detail="recipient and body required")
    result = notifier.send_email(
        recipient,
        subject,
        text,
        source_action_id=body.get("source_action_id"),
    )
    return result.dict()


@router.get("/notifications/stats")
def notification_stats(user=Depends(require_auth)):
    """Aggregate counts for dashboard tiles (24h window)."""
    from db import _db
    from psycopg2.extras import RealDictCursor

    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE channel = 'sms')   AS sms_count,
                      COUNT(*) FILTER (WHERE channel = 'email') AS email_count,
                      COUNT(*) FILTER (WHERE status = 'sent')   AS sent_count,
                      COUNT(*) FILTER (WHERE status = 'failed') AS failed_count,
                      COUNT(*) FILTER (WHERE status = 'logged') AS logged_count,
                      COUNT(*) AS total,
                      COUNT(DISTINCT recipient) AS unique_recipients
                    FROM notifications_sent
                    WHERE sent_at >= now() - INTERVAL '24 hours';
                    """
                )
                return cur.fetchone() or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
