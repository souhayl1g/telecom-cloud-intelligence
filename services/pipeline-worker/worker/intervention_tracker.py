"""Churn intervention outcome tracker.

Runs once per pipeline cycle. For each `churn_interventions` row where
outcome='pending' and created_at older than a configurable grace window,
re-fetch the subscriber's latest cem_score and flip outcome to
improved | no_change | worsened based on the delta.

This is what gives the L4 ADN agent measurable, longitudinal evidence that
interventions actually move CEM scores — answers the supervisor's
"track if CEM improves after intervention" requirement.
"""

from __future__ import annotations

import os
from typing import Optional

from worker.db import get_conn

GRACE_MINUTES = int(os.getenv("INTERVENTION_GRACE_MINUTES", "120"))
IMPROVED_DELTA = float(os.getenv("INTERVENTION_IMPROVED_DELTA", "0.05"))
WORSENED_DELTA = float(os.getenv("INTERVENTION_WORSENED_DELTA", "-0.05"))


def _classify(delta: Optional[float]) -> str:
    if delta is None:
        return "pending"
    if delta >= IMPROVED_DELTA:
        return "improved"
    if delta <= WORSENED_DELTA:
        return "worsened"
    return "no_change"


def track_outcomes() -> dict:
    """Process pending interventions older than the grace window.

    Returns a summary dict (counts) for logging by the pipeline.
    """
    summary = {"checked": 0, "improved": 0, "no_change": 0, "worsened": 0, "still_pending": 0}

    try:
        with get_conn() as conn:
            conn.autocommit = False
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, intervention_id, imsi_hash, cem_at_intervention
                    FROM churn_interventions
                    WHERE outcome = 'pending'
                      AND created_at < now() - make_interval(mins => %s)
                    ORDER BY created_at ASC
                    LIMIT 500;
                    """,
                    (GRACE_MINUTES,),
                )
                pending = cur.fetchall()
                summary["checked"] = len(pending)

                for (row_id, intervention_id, imsi_hash, cem_before) in pending:
                    cur.execute(
                        """
                        SELECT cem_score
                        FROM subscriber_features
                        WHERE imsi_hash = %s
                        ORDER BY created_at DESC
                        LIMIT 1;
                        """,
                        (imsi_hash,),
                    )
                    rec = cur.fetchone()
                    follow_up = rec[0] if rec and rec[0] is not None else None

                    if follow_up is None or cem_before is None:
                        # No fresh CEM score — leave pending, try again next cycle
                        summary["still_pending"] += 1
                        continue

                    delta = float(follow_up) - float(cem_before)
                    outcome = _classify(delta)
                    summary[outcome] = summary.get(outcome, 0) + 1

                    cur.execute(
                        """
                        UPDATE churn_interventions
                        SET follow_up_cem = %s,
                            follow_up_checked_at = now(),
                            outcome = %s
                        WHERE id = %s;
                        """,
                        (float(follow_up), outcome, row_id),
                    )
            conn.commit()
    except Exception as e:
        print(f"[intervention_tracker] error: {e}")
        summary["error"] = str(e)[:300]

    return summary
