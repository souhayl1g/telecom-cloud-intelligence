"""
Agent Service — FastAPI wrapper for NeXo Multi-Agent System
------------------------------------------------------------
Endpoints:
  POST /agent/query       → Orchestrator natural language query
  POST /agent/cem         → Direct CEMAgent call
  POST /agent/network     → Direct NetworkAgent call
  POST /agent/action      → Direct ActionAgent call
  GET  /agent/playbooks   → List available playbooks
  GET  /health            → Service health
"""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from auth import require_internal_auth
from orchestrator import Orchestrator
from agents.base import AgentIntent
from agents.cem_agent import CEMAgent
from agents.network_agent import NetworkAgent
from agents.action_agent import ActionAgent

app = FastAPI(title="NeXo Agent Service", version="3.0")

# Prometheus /metrics endpoint — scraped per prometheus.yml.
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
except ImportError:
    pass

orchestrator = Orchestrator()


# ── request models ───────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None


class AgentRequest(BaseModel):
    action: str
    params: dict = {}


# ── endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-service", "version": "3.0"}


@app.post("/agent/query")
async def agent_query(req: QueryRequest, _=Depends(require_internal_auth)):
    """Send a natural language query to the Orchestrator."""
    try:
        result = await orchestrator.process(req.query, thread_id=req.thread_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/cem")
async def agent_cem(req: AgentRequest, _=Depends(require_internal_auth)):
    """Direct call to CEMAgent."""
    agent = CEMAgent()
    intent = AgentIntent(action=req.action, params=req.params)
    result = await agent.handle(intent)
    return {
        "agent_name": result.agent_name,
        "success": result.success,
        "data": result.data,
        "summary": result.summary,
        "error": result.error,
    }


@app.post("/agent/network")
async def agent_network(req: AgentRequest, _=Depends(require_internal_auth)):
    """Direct call to NetworkAgent."""
    agent = NetworkAgent()
    intent = AgentIntent(action=req.action, params=req.params)
    result = await agent.handle(intent)
    return {
        "agent_name": result.agent_name,
        "success": result.success,
        "data": result.data,
        "summary": result.summary,
        "error": result.error,
    }


@app.post("/agent/action")
async def agent_action(req: AgentRequest, _=Depends(require_internal_auth)):
    """Direct call to ActionAgent."""
    agent = ActionAgent()
    intent = AgentIntent(action=req.action, params=req.params)
    result = await agent.handle(intent)
    return {
        "agent_name": result.agent_name,
        "success": result.success,
        "data": result.data,
        "summary": result.summary,
        "error": result.error,
    }


@app.get("/agent/playbooks")
def list_playbooks(_=Depends(require_internal_auth)):
    """List all available playbooks."""
    from agents.action_agent import PLAYBOOKS
    return {
        "playbooks": [{"id": k, "description": v} for k, v in PLAYBOOKS.items()]
    }


# ── local dev ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
