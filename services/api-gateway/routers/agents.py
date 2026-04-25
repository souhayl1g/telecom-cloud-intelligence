from fastapi import APIRouter, HTTPException, Depends, Body
import requests
from auth import require_auth
from config import AGENT_SERVICE_URL

router = APIRouter()


@router.post("/agent/query")
def agent_query(payload: dict = Body(...), user=Depends(require_auth)):
    """Orchestrator: natural language query routed to the appropriate agent."""
    try:
        resp = requests.post(f"{AGENT_SERVICE_URL}/agent/query", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Agent service unavailable: {e}")


@router.post("/agent/cem")
def agent_cem(payload: dict = Body(...), user=Depends(require_auth)):
    """Direct CEMAgent call."""
    try:
        resp = requests.post(f"{AGENT_SERVICE_URL}/agent/cem", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Agent service unavailable: {e}")


@router.post("/agent/network")
def agent_network(payload: dict = Body(...), user=Depends(require_auth)):
    """Direct NetworkAgent call."""
    try:
        resp = requests.post(f"{AGENT_SERVICE_URL}/agent/network", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Agent service unavailable: {e}")


@router.post("/agent/action")
def agent_action_direct(payload: dict = Body(...), user=Depends(require_auth)):
    """Direct ActionAgent call."""
    try:
        resp = requests.post(f"{AGENT_SERVICE_URL}/agent/action", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Agent service unavailable: {e}")


@router.get("/agent/playbooks")
def agent_playbooks(user=Depends(require_auth)):
    """List available agent playbooks."""
    try:
        resp = requests.get(f"{AGENT_SERVICE_URL}/agent/playbooks", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Agent service unavailable: {e}")
