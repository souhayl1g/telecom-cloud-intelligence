"""Internal ticketing — Postgres-backed, no external system.

Ticket IDs are TT-YYYY-NNNNN where NNNNN is from a Postgres sequence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from psycopg2.extras import RealDictCursor, Json

from db import _db


def _next_ticket_id() -> str:
    """Allocate TT-YYYY-NNNNN from tickets_seq sequence."""
    year = datetime.now(timezone.utc).year
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('tickets_seq');")
            seq = cur.fetchone()[0]
    return f"TT-{year}-{seq:05d}"


def create_ticket(
    *,
    title: str,
    description: Optional[str] = None,
    severity: str = "warning",
    source_action_id: Optional[str] = None,
    cell_id: Optional[str] = None,
    area: Optional[str] = None,
    assigned_to: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Insert a new ticket. Returns the full row."""
    if severity not in ("critical", "warning", "info"):
        severity = "warning"
    ticket_id = _next_ticket_id()
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO tickets
                    (ticket_id, title, description, severity, status,
                     source_action_id, cell_id, area, assigned_to, metadata)
                VALUES (%s, %s, %s, %s, 'open', %s, %s, %s, %s, %s)
                RETURNING *;
                """,
                (
                    ticket_id,
                    title,
                    description,
                    severity,
                    source_action_id,
                    cell_id,
                    area,
                    assigned_to,
                    Json(metadata) if metadata is not None else None,
                ),
            )
            return cur.fetchone()


def update_ticket(
    ticket_id: str,
    *,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> Optional[dict]:
    """Patch ticket status / assignment. Sets resolved_at when status is resolved|closed."""
    sets = []
    params: list = []
    if status is not None:
        if status not in ("open", "in_progress", "resolved", "closed"):
            raise ValueError(f"invalid status: {status}")
        sets.append("status = %s")
        params.append(status)
        if status in ("resolved", "closed"):
            sets.append("resolved_at = now()")
    if assigned_to is not None:
        sets.append("assigned_to = %s")
        params.append(assigned_to)
    if not sets:
        return get_ticket(ticket_id)
    params.append(ticket_id)
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                UPDATE tickets
                SET {", ".join(sets)}
                WHERE ticket_id = %s
                RETURNING *;
                """,
                tuple(params),
            )
            return cur.fetchone()


def get_ticket(ticket_id: str) -> Optional[dict]:
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tickets WHERE ticket_id = %s;", (ticket_id,))
            return cur.fetchone()


def list_tickets(
    *,
    status: Optional[str] = None,
    area: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    where = []
    params: list = []
    if status:
        where.append("status = %s")
        params.append(status)
    if area:
        where.append("area = %s")
        params.append(area)
    if severity:
        where.append("severity = %s")
        params.append(severity)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT * FROM tickets
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                tuple(params),
            )
            return list(cur.fetchall())


def ticket_stats() -> dict:
    """Aggregate counts by status + severity for dashboard tiles."""
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'open')         AS open_count,
                    COUNT(*) FILTER (WHERE status = 'in_progress')  AS in_progress_count,
                    COUNT(*) FILTER (WHERE status = 'resolved')     AS resolved_count,
                    COUNT(*) FILTER (WHERE status = 'closed')       AS closed_count,
                    COUNT(*) FILTER (WHERE severity = 'critical')   AS critical_count,
                    COUNT(*) FILTER (WHERE severity = 'warning')    AS warning_count,
                    COUNT(*) FILTER (WHERE severity = 'info')       AS info_count,
                    COUNT(*)                                         AS total
                FROM tickets;
                """
            )
            return cur.fetchone() or {}
