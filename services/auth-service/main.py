"""
Telecom NeXoligence — Auth Service
Handles user signup/login with email+password, Google OAuth, and GitHub OAuth.
Issues JWT tokens for authenticated access to all platform APIs.
"""

import json
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from jose import jwt, JWTError
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _setup_tracing() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", "auth-service"),
            "service.version": "1.0",
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)


_setup_tracing()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Telecom NeXoligence — Auth Service", version="1.0")
FastAPIInstrumentor.instrument_app(app)

# Prometheus /metrics endpoint — scraped per prometheus.yml.
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402

Instrumentator().instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)

# ---------------------------------------------------------------------------
# Configuration (env vars)
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is required")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24h default

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8002/auth/google/callback"
)

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv(
    "GITHUB_REDIRECT_URI", "http://localhost:8002/auth/github/callback"
)

# Dashboard is published on host port 3001 — the reset email link is clicked from the
# user's browser, so it must point at 3001 (port 3000 is Grafana / unused).
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3001")

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)


@contextmanager
def _db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_tables():
    """Create the users table if it doesn't exist."""
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            BIGSERIAL PRIMARY KEY,
                    email         TEXT NOT NULL UNIQUE,
                    password_hash TEXT,
                    full_name     TEXT,
                    avatar_url    TEXT,
                    provider      TEXT NOT NULL DEFAULT 'local',
                    provider_id   TEXT,
                    role          TEXT NOT NULL DEFAULT 'engineer',
                    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
                    reset_token   TEXT,
                    reset_token_expires_at TIMESTAMPTZ,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(provider, provider_id)
                );
                CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token);

                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_id);

                ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ;

                CREATE TABLE IF NOT EXISTS user_activity (
                    id          BIGSERIAL PRIMARY KEY,
                    user_id     BIGINT REFERENCES users(id) ON DELETE SET NULL,
                    user_email  TEXT,
                    actor_id    BIGINT,
                    actor_email TEXT,
                    action      TEXT NOT NULL,
                    detail      JSONB,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                CREATE INDEX IF NOT EXISTS idx_activity_created ON user_activity(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity(user_id);
            """)


@app.on_event("startup")
def on_startup():
    _ensure_tables()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    provider: str
    role: str
    is_active: bool
    created_at: str
    last_login: str | None = None


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _create_token(user_id: int, email: str, role: str) -> tuple[str, int]:
    expires = JWT_EXPIRE_MINUTES * 60
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _user_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "avatar_url": row["avatar_url"],
        "provider": row["provider"],
        "role": row["role"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "last_login": row["last_login"].isoformat() if row.get("last_login") else None,
    }


def _log_activity(
    cur, action, target_id=None, target_email=None, actor=None, detail=None
):
    """Append a row to user_activity. actor is a JWT payload (sub=user id, email)."""
    actor = actor or {}
    cur.execute(
        """INSERT INTO user_activity
             (user_id, user_email, actor_id, actor_email, action, detail)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (
            target_id,
            target_email,
            actor.get("sub"),
            actor.get("email"),
            action,
            json.dumps(detail) if detail else None,
        ),
    )


# ---------------------------------------------------------------------------
# Email/Password signup & login
# ---------------------------------------------------------------------------


@app.post("/auth/signup", response_model=TokenResponse)
def signup(req: SignupRequest):
    hashed = pwd_context.hash(req.password)
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO users (email, password_hash, full_name, provider)
                       VALUES (%s, %s, %s, 'local')
                       RETURNING *""",
                    (req.email, hashed, req.full_name),
                )
                user = cur.fetchone()
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Email already registered")

    token, expires = _create_token(user["id"], user["email"], user["role"])
    return TokenResponse(
        access_token=token,
        expires_in=expires,
        user=_user_to_dict(user),
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (req.email,))
            user = cur.fetchone()

    if not user or not user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET last_login = now() WHERE id = %s", (user["id"],)
            )
            _log_activity(
                cur,
                "login",
                user["id"],
                user["email"],
                {"sub": user["id"], "email": user["email"]},
            )

    token, expires = _create_token(user["id"], user["email"], user["role"])
    return TokenResponse(
        access_token=token,
        expires_in=expires,
        user=_user_to_dict(user),
    )


# ---------------------------------------------------------------------------
# Token verification endpoint (used by API gateway)
# ---------------------------------------------------------------------------


@app.get("/auth/me")
def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = auth_header.split(" ", 1)[1]
    payload = verify_token(token)

    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (int(payload["sub"]),))
            user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    return _user_to_dict(user)


# ---------------------------------------------------------------------------
# Admin: user & role management (admin-role guarded)
# ---------------------------------------------------------------------------

VALID_ROLES = {"engineer", "data_scientist", "admin"}


def _require_admin(request: Request) -> dict:
    """Decode the bearer token and require role == admin. 403 otherwise."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    payload = verify_token(auth_header.split(" ", 1)[1])
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload


class RoleUpdate(BaseModel):
    role: str


class ActiveUpdate(BaseModel):
    is_active: bool


class AdminCreateUser(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    role: str = "engineer"


@app.get("/auth/users")
def list_users(request: Request):
    _require_admin(request)
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users ORDER BY created_at DESC")
            return [_user_to_dict(r) for r in cur.fetchall()]


@app.post("/auth/users", response_model=UserResponse)
def admin_create_user(body: AdminCreateUser, request: Request):
    admin = _require_admin(request)
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400, detail=f"role must be one of {sorted(VALID_ROLES)}"
        )
    hashed = pwd_context.hash(body.password)
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO users (email, password_hash, full_name, provider, role)
                       VALUES (%s, %s, %s, 'local', %s) RETURNING *""",
                    (body.email, hashed, body.full_name, body.role),
                )
                user = cur.fetchone()
                _log_activity(
                    cur,
                    "user_created",
                    user["id"],
                    user["email"],
                    admin,
                    {"role": body.role},
                )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Email already registered")
    return _user_to_dict(user)


@app.patch("/auth/users/{user_id}/role", response_model=UserResponse)
def update_user_role(user_id: int, body: RoleUpdate, request: Request):
    admin = _require_admin(request)
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400, detail=f"role must be one of {sorted(VALID_ROLES)}"
        )
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "UPDATE users SET role = %s, updated_at = now() WHERE id = %s RETURNING *",
                (body.role, user_id),
            )
            user = cur.fetchone()
            if user:
                _log_activity(
                    cur,
                    "role_changed",
                    user_id,
                    user["email"],
                    admin,
                    {"role": body.role},
                )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


@app.patch("/auth/users/{user_id}/active", response_model=UserResponse)
def update_user_active(user_id: int, body: ActiveUpdate, request: Request):
    admin = _require_admin(request)
    if str(user_id) == str(admin.get("sub")) and not body.is_active:
        raise HTTPException(
            status_code=400, detail="An admin cannot deactivate their own account"
        )
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "UPDATE users SET is_active = %s, updated_at = now() WHERE id = %s RETURNING *",
                (body.is_active, user_id),
            )
            user = cur.fetchone()
            if user:
                _log_activity(
                    cur,
                    "activated" if body.is_active else "deactivated",
                    user_id,
                    user["email"],
                    admin,
                )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


class AdminUpdateUser(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


@app.patch("/auth/users/{user_id}", response_model=UserResponse)
def admin_update_user(user_id: int, body: AdminUpdateUser, request: Request):
    """Full edit: email, full_name, role, is_active, password (any subset)."""
    admin = _require_admin(request)
    is_self = str(user_id) == str(admin.get("sub"))
    if body.role is not None and body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400, detail=f"role must be one of {sorted(VALID_ROLES)}"
        )
    if is_self and body.is_active is False:
        raise HTTPException(
            status_code=400, detail="An admin cannot deactivate their own account"
        )
    if is_self and body.role is not None and body.role != "admin":
        raise HTTPException(
            status_code=400, detail="An admin cannot demote their own account"
        )

    sets, params, changed = [], [], {}
    if body.email is not None:
        sets.append("email = %s")
        params.append(body.email)
        changed["email"] = body.email
    if body.full_name is not None:
        sets.append("full_name = %s")
        params.append(body.full_name)
        changed["full_name"] = body.full_name
    if body.role is not None:
        sets.append("role = %s")
        params.append(body.role)
        changed["role"] = body.role
    if body.is_active is not None:
        sets.append("is_active = %s")
        params.append(body.is_active)
        changed["is_active"] = body.is_active
    if body.password is not None:
        sets.append("password_hash = %s")
        params.append(pwd_context.hash(body.password))
        changed["password"] = "reset"
    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets.append("updated_at = now()")
    params.append(user_id)
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"UPDATE users SET {', '.join(sets)} WHERE id = %s RETURNING *",
                    params,
                )
                user = cur.fetchone()
                if user:
                    _log_activity(
                        cur, "user_updated", user_id, user["email"], admin, changed
                    )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Email already in use")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


@app.delete("/auth/users/{user_id}")
def admin_delete_user(user_id: int, request: Request):
    admin = _require_admin(request)
    if str(user_id) == str(admin.get("sub")):
        raise HTTPException(
            status_code=400, detail="An admin cannot delete their own account"
        )
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("DELETE FROM users WHERE id = %s RETURNING email", (user_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            _log_activity(cur, "user_deleted", None, row["email"], admin)
    return {"deleted": True, "email": row["email"]}


@app.get("/auth/activity")
def list_activity(request: Request, limit: int = 50):
    _require_admin(request)
    limit = max(1, min(limit, 200))
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM user_activity ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return [_activity_to_dict(r) for r in cur.fetchall()]


@app.get("/auth/users/{user_id}/activity")
def list_user_activity(user_id: int, request: Request, limit: int = 50):
    _require_admin(request)
    limit = max(1, min(limit, 200))
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM user_activity
                     WHERE user_id = %s OR actor_id = %s
                     ORDER BY created_at DESC LIMIT %s""",
                (user_id, user_id, limit),
            )
            return [_activity_to_dict(r) for r in cur.fetchall()]


def _activity_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "user_email": row["user_email"],
        "actor_id": row["actor_id"],
        "actor_email": row["actor_email"],
        "action": row["action"],
        "detail": row["detail"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


# ---------------------------------------------------------------------------
# Google OAuth2
# ---------------------------------------------------------------------------


@app.get("/auth/google")
def google_login(response: Response):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    state = secrets.token_urlsafe(32)
    params = (
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    resp = RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
    )
    resp.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        max_age=600,
        samesite="lax",
        secure=False,  # Set True in production (HTTPS)
    )
    return resp


@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str, state: str = ""):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or not secrets.compare_digest(cookie_state, state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Failed to exchange Google auth code"
            )
        tokens = token_resp.json()

        # Get user info
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Failed to fetch Google user info"
            )
        guser = userinfo_resp.json()

    user = _upsert_oauth_user(
        email=guser["email"],
        full_name=guser.get("name", ""),
        avatar_url=guser.get("picture", ""),
        provider="google",
        provider_id=guser["id"],
    )

    token, expires = _create_token(user["id"], user["email"], user["role"])
    resp = RedirectResponse(
        url=f"{FRONTEND_URL}/auth/callback?token={token}&expires_in={expires}"
    )
    resp.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        max_age=expires,
        samesite="lax",
        secure=False,  # Set True in production (HTTPS)
    )
    resp.delete_cookie(key="oauth_state")
    return resp


# ---------------------------------------------------------------------------
# GitHub OAuth2
# ---------------------------------------------------------------------------


@app.get("/auth/github")
def github_login(response: Response):
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")

    state = secrets.token_urlsafe(32)
    params = (
        f"client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=read:user%20user:email"
        f"&state={state}"
    )
    resp = RedirectResponse(url=f"https://github.com/login/oauth/authorize?{params}")
    resp.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        max_age=600,
        samesite="lax",
        secure=False,  # Set True in production (HTTPS)
    )
    return resp


@app.get("/auth/github/callback")
async def github_callback(request: Request, code: str, state: str = ""):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")

    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or not secrets.compare_digest(cookie_state, state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Failed to exchange GitHub auth code"
            )
        tokens = token_resp.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token from GitHub")

        # Get user profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub user")
        ghuser = user_resp.json()

        # Get primary email (may be private)
        email = ghuser.get("email")
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            if emails_resp.status_code == 200:
                for em in emails_resp.json():
                    if em.get("primary") and em.get("verified"):
                        email = em["email"]
                        break

        if not email:
            raise HTTPException(
                status_code=400, detail="No verified email found on GitHub account"
            )

    user = _upsert_oauth_user(
        email=email,
        full_name=ghuser.get("name") or ghuser.get("login", ""),
        avatar_url=ghuser.get("avatar_url", ""),
        provider="github",
        provider_id=str(ghuser["id"]),
    )

    token, expires = _create_token(user["id"], user["email"], user["role"])
    resp = RedirectResponse(
        url=f"{FRONTEND_URL}/auth/callback?token={token}&expires_in={expires}"
    )
    resp.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        max_age=expires,
        samesite="lax",
        secure=False,  # Set True in production (HTTPS)
    )
    resp.delete_cookie(key="oauth_state")
    return resp


# ---------------------------------------------------------------------------
# OAuth upsert helper
# ---------------------------------------------------------------------------


def _upsert_oauth_user(
    email: str,
    full_name: str,
    avatar_url: str,
    provider: str,
    provider_id: str,
) -> dict:
    """Insert new OAuth user or update existing one. Returns user dict."""
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if user exists by provider+provider_id
            cur.execute(
                "SELECT * FROM users WHERE provider = %s AND provider_id = %s",
                (provider, provider_id),
            )
            user = cur.fetchone()

            if user:
                # Update profile info on each login
                cur.execute(
                    """UPDATE users
                       SET full_name = %s, avatar_url = %s, updated_at = now()
                       WHERE id = %s
                       RETURNING *""",
                    (full_name, avatar_url, user["id"]),
                )
                return cur.fetchone()

            # Check if email already exists with a different provider
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing = cur.fetchone()

            if existing:
                # Link this OAuth provider to the existing account.
                # Preserve original provider so local password login continues to work.
                cur.execute(
                    """UPDATE users
                       SET provider_id = %s,
                           avatar_url = COALESCE(avatar_url, %s),
                           updated_at = now()
                       WHERE id = %s
                       RETURNING *""",
                    (provider_id, avatar_url, existing["id"]),
                )
                return cur.fetchone()

            # Brand new user
            cur.execute(
                """INSERT INTO users (email, full_name, avatar_url, provider, provider_id)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING *""",
                (email, full_name, avatar_url, provider, provider_id),
            )
            return cur.fetchone()


# ---------------------------------------------------------------------------
# Forgot password
# ---------------------------------------------------------------------------

# SMTP config (shared with api-gateway notifier)
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip().replace(" ", "")
SMTP_FROM = os.getenv(
    "SMTP_FROM", "NeXo Telecom Intelligence <nexo-noreply@tunisietelecom.tn>"
).strip()
FRONTEND_RESET_URL = os.getenv("FRONTEND_RESET_URL", f"{FRONTEND_URL}/reset-password")

# Dev-mode: include reset link in API response when SMTP fails so the UI can
# display it.  Safe for local development / defense demos — never true in prod.
DEV_SHOW_FALLBACK_LINK = os.getenv("DEV_SHOW_FALLBACK_LINK", "false").lower() in (
    "1",
    "true",
    "yes",
)


def _send_reset_email(to_email: str, token: str) -> dict:
    """Send password reset email via SMTP.  Returns status dict for the caller.

    Return value keys:
        sent      — bool, whether the email was accepted by the SMTP server
        provider  — 'smtp' | 'console'
        error     — error message when sent==False (None otherwise)
        link      — the reset link (always present; UI shows this in dev mode)
    """
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib

    reset_link = f"{FRONTEND_RESET_URL}?token={token}"
    subject = "NeXo — Reset Your Password"
    body_text = (
        f"Hello,\n\n"
        f"You requested a password reset for your NeXo Telecom Intelligence account.\n\n"
        f"Click the link below to reset your password (valid for 15 minutes):\n\n"
        f"{reset_link}\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"— NeXo Security Team"
    )
    body_html = (
        f'<html><body style="font-family:system-ui,sans-serif;max-width:480px;margin:24px auto;color:#1a1a2e">'
        f'<h2 style="color:#00D4FF">NeXo Password Reset</h2>'
        f"<p>You requested a password reset for your NeXo account.</p>"
        f'<p><a href="{reset_link}" style="display:inline-block;padding:12px 24px;background:#00D4FF;color:#fff;text-decoration:none;border-radius:8px;font-weight:600">Reset Password</a></p>'
        f'<p style="color:#666;font-size:13px">Or copy this link:<br><code style="background:#f4f4f8;padding:4px 8px;border-radius:4px">{reset_link}</code></p>'
        f'<p style="color:#666;font-size:13px">This link expires in 15 minutes. If you did not request this, ignore this email.</p>'
        f"<p>— NeXo Security Team</p>"
        f"</body></html>"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM, [to_email], msg.as_string())
            print(f"[auth] Reset email sent to {to_email}")
            return {"sent": True, "provider": "smtp", "error": None, "link": reset_link}
        except Exception as e:
            err = str(e)
            print(f"[auth] SMTP send failed: {err}")
            # Fall through to console fallback

    # Console fallback (always available)
    print(f"[auth] RESET EMAIL (console fallback) to={to_email}")
    print(f"[auth]   Link: {reset_link}")
    return {
        "sent": False,
        "provider": "console",
        "error": "SMTP not configured or credentials rejected. Check auth-service logs.",
        "link": reset_link,
    }


@app.post("/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    """Send a password reset link to the user's email."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)

    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (req.email,))
            user = cur.fetchone()
            if not user:
                # Don't reveal whether email exists
                return {
                    "ok": True,
                    "detail": "If an account exists, a reset link has been sent.",
                }
            if user.get("provider") != "local" or not user.get("password_hash"):
                raise HTTPException(
                    status_code=400,
                    detail="Password reset is only available for local accounts",
                )
            cur.execute(
                "UPDATE users SET reset_token = %s, reset_token_expires_at = %s WHERE id = %s",
                (token, expires, user["id"]),
            )

    result = _send_reset_email(req.email, token)
    resp = {"ok": True, "detail": "If an account exists, a reset link has been sent."}
    if DEV_SHOW_FALLBACK_LINK and not result["sent"]:
        resp["fallback_link"] = result["link"]
        resp["fallback_provider"] = result["provider"]
    return resp


@app.post("/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    """Reset password using a valid token."""
    hashed = pwd_context.hash(req.password)
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM users WHERE reset_token = %s AND reset_token_expires_at > now()",
                (req.token,),
            )
            user = cur.fetchone()
            if not user:
                raise HTTPException(
                    status_code=400, detail="Invalid or expired reset token"
                )
            cur.execute(
                "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expires_at = NULL, updated_at = now() WHERE id = %s RETURNING *",
                (hashed, user["id"]),
            )
            updated = cur.fetchone()

    token, expires = _create_token(updated["id"], updated["email"], updated["role"])
    return TokenResponse(
        access_token=token,
        expires_in=expires,
        user=_user_to_dict(updated),
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth"}
