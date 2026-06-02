"""Internal auth — shared API key for service-to-service calls."""
import os
from fastapi import Header, HTTPException

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")


def require_internal_auth(x_internal_key: str = Header(None)):
    if not x_internal_key or x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid internal API key")
    return True
