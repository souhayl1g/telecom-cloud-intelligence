"""
Orchestrator — LLM-Powered Intent Router
----------------------------------------
Uses Qwen2.5:7b via Ollama to:
  1. Classify user intent into action categories
  2. Extract entities (subscriber, area, cell, month)
  3. Dispatch to the appropriate agent
  4. Synthesize results into natural language

Fallback: if Ollama is unavailable, uses rule-based routing.
"""

import json
import os
from typing import Optional

import requests

from agents.base import AgentIntent, AgentResult
from agents.cem_agent import CEMAgent
from agents.network_agent import NetworkAgent
from agents.action_agent import ActionAgent

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# Agent registry
AGENTS = {
    "CEMAgent": CEMAgent(),
    "NetworkAgent": NetworkAgent(),
    "ActionAgent": ActionAgent(),
}

# Simple rule-based fallback mapping
KEYWORD_MAP = {
    "subscriber": ("CEMAgent", "analyze_subscriber"),
    "imsi": ("CEMAgent", "analyze_subscriber"),
    "customer": ("CEMAgent", "analyze_subscriber"),
    "experience": ("CEMAgent", "score_experience"),
    "cem": ("CEMAgent", "area_cem_summary"),
    "nps": ("CEMAgent", "predict_nps"),
    "underserved": ("CEMAgent", "find_underserved"),
    "cell": ("NetworkAgent", "monitor_cells"),
    "network": ("NetworkAgent", "area_health"),
    "kpi": ("NetworkAgent", "monitor_cells"),
    "anomaly": ("NetworkAgent", "detect_anomaly"),
    "capacity": ("NetworkAgent", "capacity_forecast"),
    "health": ("NetworkAgent", "area_health"),
    "playbook": ("ActionAgent", "execute_playbook"),
    "action": ("ActionAgent", "list_playbooks"),
    "approve": ("ActionAgent", "approve_action"),
    "reject": ("ActionAgent", "reject_action"),
    "escalate": ("ActionAgent", "escalate"),
}


def _ollama_generate(prompt: str, json_mode: bool = True) -> Optional[dict]:
    """Call Ollama generate endpoint. Returns parsed JSON or None on failure."""
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 256},
        }
        if json_mode:
            payload["format"] = "json"

        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "{}").strip()
        return json.loads(text)
    except Exception as e:
        print(f"[orchestrator] Ollama error: {e}")
        return None


def _build_intent_prompt(query: str) -> str:
    return f"""You are the intent classifier for a telecom AI operations platform.
Classify the user's query into ONE agent and ONE action.

Available agents and actions:
- CEMAgent: analyze_subscriber, score_experience, find_underserved, predict_nps, area_cem_summary
- NetworkAgent: monitor_cells, detect_anomaly, capacity_forecast, correlate_with_cem, area_health
- ActionAgent: execute_playbook, auto_remediate, escalate, list_playbooks, approve_action, reject_action

Extract entities:
- imsi_hash: if a subscriber hash is mentioned
- area: Tunisian governorate (e.g. Tunis, Sfax, Nabeul)
- month_year: e.g. 2026-03 (default to 2026-03 if not specified)
- playbook_id: if a playbook is mentioned
- action_id: if an action ID is mentioned

Respond ONLY with valid JSON in this exact format:
{{"agent": "CEMAgent", "action": "analyze_subscriber", "params": {{"imsi_hash": "abc123", "month_year": "2026-03"}}}}

User query: {query}
"""


def _rule_classify(query: str) -> dict:
    """Fallback rule-based classifier."""
    q = query.lower()
    for keyword, (agent, action) in KEYWORD_MAP.items():
        if keyword in q:
            params = {}
            # naive entity extraction
            if "tunis" in q:
                params["area"] = "Tunis"
            elif "sfax" in q:
                params["area"] = "Sfax"
            elif "nabeul" in q:
                params["area"] = "NABEUL"
            elif "bizerte" in q:
                params["area"] = "Bizerte"
            elif "sousse" in q:
                params["area"] = "Sousse"

            if "2026-02" in q:
                params["month_year"] = "2026-02"
            elif "2026-04" in q:
                params["month_year"] = "2026-04"
            elif "2026-05" in q:
                params["month_year"] = "2026-05"
            elif "2026-06" in q:
                params["month_year"] = "2026-06"
            else:
                params["month_year"] = "2026-03"

            # Try to extract an imsi-like hash (32 hex chars)
            import re
            hashes = re.findall(r"[a-f0-9]{{32}}", q)
            if hashes:
                params["imsi_hash"] = hashes[0]

            return {"agent": agent, "action": action, "params": params}

    return {"agent": "CEMAgent", "action": "area_cem_summary", "params": {"area": "Tunis", "month_year": "2026-03"}}


class Orchestrator:
    async def process(self, query: str, thread_id: Optional[str] = None) -> dict:
        """Process a natural language query through the multi-agent system."""

        # 1. Intent classification (LLM + fallback)
        prompt = _build_intent_prompt(query)
        classification = _ollama_generate(prompt)
        if classification is None:
            classification = _rule_classify(query)

        agent_name = classification.get("agent", "CEMAgent")
        action = classification.get("action", "area_cem_summary")
        params = classification.get("params", {})

        # 2. Agent dispatch
        agent = AGENTS.get(agent_name)
        if not agent:
            return {
                "success": False,
                "error": f"Unknown agent: {agent_name}",
                "classification": classification,
            }

        intent = AgentIntent(action=action, params=params)
        result = await agent.handle(intent)

        # 3. Synthesize response
        synthesized = self._synthesize(query, classification, result)

        return {
            "success": result.success,
            "classification": classification,
            "agent_result": {
                "agent_name": result.agent_name,
                "success": result.success,
                "data": result.data,
                "summary": result.summary,
                "error": result.error,
            },
            "response": synthesized,
            "thread_id": thread_id,
        }

    def _synthesize(self, query: str, classification: dict, result: AgentResult) -> str:
        """Create a natural language response from agent result."""
        if not result.success:
            return f"I couldn't complete that request. {result.error or 'Unknown error.'}"

        agent_name = result.agent_name
        summary = result.summary
        data = result.data

        # Add helpful context based on agent type
        extras = []
        if agent_name == "CEMAgent" and "cem_score" in data:
            score = data["cem_score"]
            if score > 0.7:
                extras.append("This subscriber has a good experience profile.")
            elif score > 0.4:
                extras.append("There is room for improvement in this subscriber's experience.")
            else:
                extras.append("This subscriber is experiencing significant service degradation.")

            if data.get("usim_bottleneck"):
                extras.append("A SIM upgrade to USIM would unlock better RAT access.")

        if agent_name == "NetworkAgent" and "health_score" in data:
            hs = data["health_score"]
            if hs > 80:
                extras.append("The network in this area is performing well.")
            elif hs > 50:
                extras.append("Some cells may need attention in the coming weeks.")
            else:
                extras.append("This area requires urgent network optimization.")

        if agent_name == "ActionAgent" and data.get("decision"):
            extras.append(f"Decision: {data['decision']}.")

        response = summary
        if extras:
            response += " " + " ".join(extras)

        return response
