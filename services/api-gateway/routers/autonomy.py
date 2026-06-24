"""L4 closed-loop autonomy router.

Turns the L3 (human-approved) agent into a genuine L4 closed loop. The agent
already detects (generateActions) and can execute real playbooks
(actions.execute_action). What was missing is the *unattended* decision→execute
link. This router adds it — but only inside a bounded safety envelope:

    armed                -> master switch; nothing runs unless TRUE
    confidence_threshold -> only act on signals the models are sure about
    playbook_whitelist   -> ONLY these playbooks may self-execute (empty => none)
    max_actions_per_hour -> rate limit; the loop cannot run away
    kill_switch          -> emergency stop for the autonomous path

This is the TM Forum L4 definition in code: the system handles most scenarios
autonomously, the human owns the envelope (which playbooks are pre-authorised)
and the exceptional cases. Every unattended execution is stamped
decided_by='L4-autonomous' for audit.

Guardrails are enforced HERE, server-side — never trusting the client.
"""

from fastapi import APIRouter, Depends, Body, HTTPException
from psycopg2.extras import RealDictCursor

from db import _db
from auth import require_auth
from routers.actions import execute_action

router = APIRouter()

# Actions eligible for unattended execution must be in one of these states.
_RUNNABLE_STATES = ("pending", "auto_approved")


def _load_config(cur) -> dict:
    """Read the singleton autonomy config, self-healing if the row is missing."""
    cur.execute("SELECT * FROM agent_autonomy_config WHERE id = 1;")
    cfg = cur.fetchone()
    if not cfg:
        cur.execute(
            "INSERT INTO agent_autonomy_config (id) VALUES (1) "
            "ON CONFLICT (id) DO NOTHING RETURNING *;"
        )
        cfg = cur.fetchone() or {
            "armed": False,
            "confidence_threshold": 0.85,
            "playbook_whitelist": [],
            "max_actions_per_hour": 10,
            "kill_switch": False,
        }
    return cfg


def _l4_eligible(action: dict, cfg: dict) -> tuple[bool, str]:
    """Single source of truth for 'can this action run unattended?'.

    Returns (eligible, reason_if_not). The whitelist is the safety envelope:
    an empty whitelist means NOTHING self-executes, by design.
    """
    pb = action.get("playbook_id")
    if not pb:
        return False, "no playbook bound"
    whitelist = cfg.get("playbook_whitelist") or []
    if pb not in whitelist:
        return False, f"playbook '{pb}' not in whitelist"
    conf = action.get("confidence")
    threshold = cfg.get("confidence_threshold") or 0.0
    if conf is None or conf < threshold:
        return False, f"confidence {conf} < threshold {threshold}"
    if action.get("status") not in _RUNNABLE_STATES:
        return False, f"status '{action.get('status')}' not runnable"
    return True, ""


@router.get("/autonomy/config")
def get_autonomy_config(user=Depends(require_auth)):
    """Return the current L4 safety envelope."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                return _load_config(cur)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/autonomy/config")
def update_autonomy_config(body: dict = Body(...), user=Depends(require_auth)):
    """Arm/disarm the closed loop and tune the envelope.

    Accepts any subset of: armed, confidence_threshold, playbook_whitelist,
    max_actions_per_hour, kill_switch. Validates each so a bad client payload
    cannot widen the envelope unexpectedly.
    """
    allowed = {
        "armed": bool,
        "confidence_threshold": float,
        "playbook_whitelist": list,
        "max_actions_per_hour": int,
        "kill_switch": bool,
    }
    sets, params = [], []
    for key, caster in allowed.items():
        if key not in body:
            continue
        val = body[key]
        try:
            if caster is bool:
                val = bool(val)
            elif caster is float:
                val = float(val)
                if not (0.0 <= val <= 1.0):
                    raise ValueError("confidence_threshold must be in [0,1]")
            elif caster is int:
                val = int(val)
                if val < 0:
                    raise ValueError("max_actions_per_hour must be >= 0")
            elif caster is list:
                if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                    raise ValueError("playbook_whitelist must be a list of strings")
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"{key}: {e}")
        sets.append(f"{key} = %s")
        params.append(val)

    if not sets:
        raise HTTPException(status_code=400, detail="No valid config fields provided")

    sets.append("updated_at = now()")
    sets.append("updated_by = %s")
    params.append(user.get("sub", "system"))

    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                _load_config(cur)  # ensure row exists
                cur.execute(
                    f"UPDATE agent_autonomy_config SET {', '.join(sets)} "
                    f"WHERE id = 1 RETURNING *;",
                    params,
                )
                return cur.fetchone()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/autonomy/auto-run")
def auto_run(user=Depends(require_auth)):
    """The closed-loop tick.

    Finds runnable actions that pass the envelope and executes them unattended,
    stamping each decided_by='L4-autonomous'. Returns per-action verdicts so the
    UI can show exactly what the machine did and what it refused (and why).

    Refuses entirely when disarmed or the kill-switch is engaged — those checks
    live here, server-side, so a client cannot bypass them.
    """
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cfg = _load_config(cur)

                if cfg.get("kill_switch"):
                    return {"armed": cfg.get("armed"), "kill_switch": True,
                            "executed": [], "skipped": [], "reason": "kill-switch engaged"}
                if not cfg.get("armed"):
                    return {"armed": False, "kill_switch": False,
                            "executed": [], "skipped": [], "reason": "closed loop disarmed"}

                # Rate limit: how many autonomous executions in the trailing hour?
                cur.execute(
                    "SELECT count(*) AS n FROM agent_actions "
                    "WHERE decided_by = 'L4-autonomous' "
                    "AND resolved_at >= now() - INTERVAL '1 hour';"
                )
                used = (cur.fetchone() or {}).get("n", 0)
                budget = max(0, (cfg.get("max_actions_per_hour") or 0) - used)

                # Candidate actions, most severe + most confident first.
                cur.execute(
                    """
                    SELECT * FROM agent_actions
                    WHERE status IN %s
                    ORDER BY CASE severity WHEN 'critical' THEN 0
                                           WHEN 'warning'  THEN 1 ELSE 2 END,
                             confidence DESC NULLS LAST
                    LIMIT 50;
                    """,
                    (_RUNNABLE_STATES,),
                )
                candidates = cur.fetchall()

        executed, skipped = [], []
        for action in candidates:
            aid = action["action_id"]
            ok, reason = _l4_eligible(action, cfg)
            if not ok:
                skipped.append({"action_id": aid, "reason": reason})
                continue
            if budget <= 0:
                skipped.append({"action_id": aid, "reason": "hourly rate limit reached"})
                continue
            # Reuse the full playbook engine; mark the decision as autonomous.
            try:
                execute_action(aid, user={"sub": "L4-autonomous"})
                with _db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE agent_actions SET decided_by = 'L4-autonomous' "
                            "WHERE action_id = %s;",
                            (aid,),
                        )
                budget -= 1
                executed.append({"action_id": aid, "playbook_id": action.get("playbook_id"),
                                 "title": action.get("title")})
            except HTTPException as he:
                skipped.append({"action_id": aid, "reason": f"execute failed: {he.detail}"})
            except Exception as e:
                skipped.append({"action_id": aid, "reason": f"execute error: {e}"})

        return {"armed": True, "kill_switch": False,
                "executed": executed, "skipped": skipped,
                "rate_limit_remaining": budget}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
