"""
Telecom NeXoligence — Auth Service
Handles user signup/login with email+password, Google OAuth, and GitHub OAuth.
Issues JWT tokens for authenticated access to all platform APIs.
"""

import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Request
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
    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "auth-service"),
        "service.version": "1.0",
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


_setup_tracing()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Telecom NeXoligence — Auth Service", version="1.0")
FastAPIInstrumentor.instrument_app(app)

# Prometheus /metrics endpoint — scraped per prometheus.yml.
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# ---------------------------------------------------------------------------
# Configuration (env vars)
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
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

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

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
                    role          TEXT NOT NULL DEFAULT 'viewer',
                    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(provider, provider_id)
                );

                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_id);
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
    }


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
# Google OAuth2
# ---------------------------------------------------------------------------


@app.get("/auth/google")
def google_login():
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
    return RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
    )


@app.get("/auth/google/callback")
async def google_callback(code: str, state: str = ""):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

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
    # Redirect to frontend with token
    return RedirectResponse(
        url=f"{FRONTEND_URL}/auth/callback?token={token}&expires_in={expires}"
    )


# ---------------------------------------------------------------------------
# GitHub OAuth2
# ---------------------------------------------------------------------------


@app.get("/auth/github")
def github_login():
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")

    state = secrets.token_urlsafe(32)
    params = (
        f"client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=read:user%20user:email"
        f"&state={state}"
    )
    return RedirectResponse(url=f"https://github.com/login/oauth/authorize?{params}")


@app.get("/auth/github/callback")
async def github_callback(code: str, state: str = ""):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")

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
    return RedirectResponse(
        url=f"{FRONTEND_URL}/auth/callback?token={token}&expires_in={expires}"
    )


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
                # Link this OAuth provider to the existing account
                cur.execute(
                    """UPDATE users
                       SET provider = %s, provider_id = %s,
                           avatar_url = COALESCE(avatar_url, %s),
                           updated_at = now()
                       WHERE id = %s
                       RETURNING *""",
                    (provider, provider_id, avatar_url, existing["id"]),
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
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth"}
