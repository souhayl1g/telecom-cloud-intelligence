"""REST endpoints for internal tickets."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from auth import require_auth
from services import ticketing

router = APIRouter()


@router.get("/tickets")
def list_tickets(
    status: str = Query(default=None),
    area: str = Query(default=None),
    severity: str = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(require_auth),
):
    rows = ticketing.list_tickets(
        status=status, area=area, severity=severity, limit=limit
    )
    return {"tickets": rows, "count": len(rows)}


@router.get("/tickets/stats")
def stats(user=Depends(require_auth)):
    return ticketing.ticket_stats()


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str, user=Depends(require_auth)):
    row = ticketing.get_ticket(ticket_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return row


@router.post("/tickets")
def create_ticket(body: dict = Body(...), user=Depends(require_auth)):
    title = body.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title required")
    try:
        return ticketing.create_ticket(
            title=title,
            description=body.get("description"),
            severity=body.get("severity", "warning"),
            source_action_id=body.get("source_action_id"),
            cell_id=body.get("cell_id"),
            area=body.get("area"),
            assigned_to=body.get("assigned_to"),
            metadata=body.get("metadata"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tickets/{ticket_id}")
def patch_ticket(ticket_id: str, body: dict = Body(...), user=Depends(require_auth)):
    try:
        row = ticketing.update_ticket(
            ticket_id,
            status=body.get("status"),
            assigned_to=body.get("assigned_to"),
        )
        if not row:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return row
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
