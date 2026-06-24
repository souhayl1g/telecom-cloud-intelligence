from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from config import JWT_SECRET, JWT_ALGORITHM

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    try:
        return jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_auth(user=Depends(get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_role(*roles: str):
    """Dependency factory: require an authenticated user whose JWT role is in `roles`.

    Admin is always allowed (super-role). Usage:
        @router.get(..., dependencies=[Depends(require_role("data_scientist"))])
    """
    allowed = set(roles) | {"admin"}

    def _checker(user=Depends(require_auth)):
        if user.get("role") not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of roles: {sorted(allowed)}",
            )
        return user

    return _checker
