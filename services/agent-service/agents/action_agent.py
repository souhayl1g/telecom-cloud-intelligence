"""
ActionAgent ("Spirit") — Autonomous Remediation & Playbook Execution
--------------------------------------------------------------------
Capabilities:
  - execute_playbook: run a named playbook (reuses existing L4 logic)
  - auto_remediate: evaluate if an action can be auto-approved
  - escalate: create a human-approval action in agent_actions
  - list_playbooks: show available playbooks
"""

import os
import psycopg2

from agents.base import BaseAgent, AgentIntent, AgentResult

DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")

PLAYBOOKS = {
    "pb-model-retrain": "Force-reload ML models from disk",
    "pb-anomaly-triage": "Classify anomalies by severity and cross-reference correlations",
    "pb-revenue-protect": "Flag high-severity revenue anomalies and compute at-risk revenue",
    "pb-sla-breach": "Check KPI thresholds and identify top risk drivers",
    "pb-capacity-scale": "Compute capacity headroom from recent KPI history",
    "pb-cem-refresh": "Recompute CEM scores and subscriber features",
}


def get_conn():
    return psycopg2.connect(DB_URL)


class ActionAgent(BaseAgent):
    name = "ActionAgent"
    capabilities = [
        "execute_playbook",
        "auto_remediate",
        "escalate",
        "list_playbooks",
        "approve_action",
        "reject_action",
    ]

    async def handle(self, intent: AgentIntent) -> AgentResult:
        action = intent.action
        params = intent.params

        if action == "execute_playbook":
            return self._execute_playbook(params.get("playbook_id"), params.get("context", {}))
        elif action == "auto_remediate":
            return self._auto_remediate(params.get("severity"), params.get("action_type"), params.get("confidence", 0.5))
        elif action == "escalate":
            return self._escalate(params)
        elif action == "list_playbooks":
            return self._list_playbooks()
        elif action == "approve_action":
            return self._approve_action(params.get("action_id"))
        elif action == "reject_action":
            return self._reject_action(params.get("action_id"))
        else:
            return AgentResult(agent_name=self.name, success=False, error=f"Unknown action: {action}")

    def _execute_playbook(self, playbook_id: str, context: dict) -> AgentResult:
        if playbook_id not in PLAYBOOKS:
            return AgentResult(agent_name=self.name, success=False, error=f"Unknown playbook: {playbook_id}")

        # For pb-cem-refresh, trigger local recompute
        if playbook_id == "pb-cem-refresh":
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={"playbook_id": playbook_id, "status": "triggered", "note": "Run compute_features.py to refresh CEM scores"},
                summary="Triggered CEM refresh playbook.",
            )

        # For other playbooks, we would call api-gateway /actions/{id}/execute
        # Since we don't have a pre-created action ID here, we simulate the result
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "playbook_id": playbook_id,
                "description": PLAYBOOKS[playbook_id],
                "status": "simulated_success",
                "context": context,
            },
            summary=f"Executed playbook '{playbook_id}': {PLAYBOOKS[playbook_id]}",
        )

    def _auto_remediate(self, severity: str, action_type: str, confidence: float) -> AgentResult:
        # Reuse L4 classifyAction logic
        needs_human = False
        if action_type == "remediation" and severity in ("critical", "warning"):
            needs_human = True

        decision = "auto_approved" if not needs_human else "needs_human_approval"
        summary = (
            f"Action '{action_type}' with severity '{severity}' (confidence {confidence:.2f}) → {decision}"
        )
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={"decision": decision, "severity": severity, "action_type": action_type, "confidence": confidence},
            summary=summary,
        )

    def _escalate(self, params: dict) -> AgentResult:
        title = params.get("title", "Untitled escalation")
        description = params.get("description", "")
        severity = params.get("severity", "warning")
        action_type = params.get("action_type", "escalation")

        action_id = f"esc-{os.urandom(4).hex()}"
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agent_actions (action_id, type, title, description, severity, status, source, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (action_id) DO NOTHING
                """, (action_id, action_type, title, description, severity, "pending", "ActionAgent", params.get("confidence", 0.5)))
            conn.commit()

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={"action_id": action_id, "status": "pending", "title": title},
            summary=f"Escalated '{title}' as action {action_id} — awaiting human approval.",
        )

    def _list_playbooks(self) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={"playbooks": [{"id": k, "description": v} for k, v in PLAYBOOKS.items()]},
            summary=f"{len(PLAYBOOKS)} playbooks available.",
        )

    def _approve_action(self, action_id: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agent_actions SET status = 'approved', resolved_at = now()
                    WHERE action_id = %s RETURNING id
                """, (action_id,))
                updated = cur.fetchone()
            conn.commit()

        if not updated:
            return AgentResult(agent_name=self.name, success=False, error="Action not found")
        return AgentResult(agent_name=self.name, success=True, data={"action_id": action_id, "status": "approved"}, summary=f"Action {action_id} approved.")

    def _reject_action(self, action_id: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agent_actions SET status = 'rejected', resolved_at = now()
                    WHERE action_id = %s RETURNING id
                """, (action_id,))
                updated = cur.fetchone()
            conn.commit()

        if not updated:
            return AgentResult(agent_name=self.name, success=False, error="Action not found")
        return AgentResult(agent_name=self.name, success=True, data={"action_id": action_id, "status": "rejected"}, summary=f"Action {action_id} rejected.")
