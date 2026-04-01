  # Telecom Cloud Intelligence Platform — Phase 4 Report
  ## Authentication System, Dashboard Integration & CI/CD Pipeline

  **Date:** 2026-04-01
  **Author:** Souhayl Guenichi
  **Phase:** 4 — Security, Frontend Auth & Automation

  ---

  ## Table of Contents
  1. [Executive Summary](#1-executive-summary)
  2. [What We Had (Phase 1–3 Recap)](#2-what-we-had-phase-13-recap)
  3. [What We Built in Phase 4](#3-what-we-built-in-phase-4)
  4. [Authentication System — Deep Dive](#4-authentication-system--deep-dive)
  5. [Dashboard Signup/Login — Frontend Integration](#5-dashboard-signuplogin--frontend-integration)
  6. [GitHub Actions CI/CD — Full Explanation](#6-github-actions-cicd--full-explanation)
  7. [Updated Architecture](#7-updated-architecture)
  8. [Database Schema Changes](#8-database-schema-changes)
  9. [How to Use Everything](#9-how-to-use-everything)
  10. [What Comes Next (Phase 5–6)](#10-what-comes-next-phase-56)

  ---

  ## 1. Executive Summary

  Phase 4 adds three critical capabilities:

  1. **Full authentication system** — A new `auth-service` microservice (FastAPI, port 8002) supporting signup/login via email+password, Google OAuth2, and GitHub OAuth2. All API endpoints are now JWT-protected.

  2. **Dashboard signup/login UI** — The Next.js dashboard now has real signup and login pages connected to the auth service. Google and GitHub OAuth buttons work end-to-end. JWT tokens are stored in httpOnly cookies and sent with every API request automatically.

  3. **Automated CI/CD pipeline** — A 6-stage GitHub Actions workflow that lints, tests, builds, integration-tests, security-scans, and deploys automatically on every code push.

  ---

  ## 2. What We Had (Phase 1–3 Recap)

  ### Phase 1 — Foundation
  - Docker Compose stack with 7 services (PostgreSQL, MinIO, API Gateway, AI Service, Pipeline Worker, Prometheus, Grafana)
  - 7 PostgreSQL tables for pipeline metadata and analytics
  - 3-layer MinIO data lake (raw -> processed -> curated)

  ### Phase 2 — Real ML Inference
  - GradientBoostingRegressor for SLA risk scoring (v2.0)
  - 2x IsolationForest for OSS anomaly + BSS revenue anomaly detection
  - 22-step pipeline orchestrator running every 2 minutes

  ### Phase 3 — Alignment & Documentation
  - Complete API gateway with 7 endpoints (all open, no auth)
  - Dashboard with login page (dummy admin/admin check, no real users)
  - Google/GitHub buttons existed in UI but did nothing

  ### What Was Missing
  | Gap | Risk |
  |-----|------|
  | No real authentication | Anyone could access all data |
  | No user management | No real user accounts, no signup |
  | Login was fake | Hardcoded admin/admin, no database |
  | Social buttons were decorative | Google/GitHub buttons had no backend |
  | No CI/CD | Manual testing only, no quality gates |

  ---

  ## 3. What We Built in Phase 4

  ### New Files Created

  ```
  services/auth-service/                  <- NEW backend microservice
    main.py                               (310 lines - full auth logic)
    requirements.txt                      (8 dependencies)
    Dockerfile                            (production container)

  dashboard/app/signup/page.tsx           <- NEW signup page
  dashboard/app/auth/callback/page.tsx    <- NEW OAuth callback handler

  .github/workflows/ci-cd.yml            <- NEW CI/CD pipeline (220 lines)
  ```

  ### Files Modified

  | File | Change |
  |------|--------|
  | `docker-compose.yml` | Added auth-service + auth env vars |
  | `services/api-gateway/main.py` | Added JWT middleware on all endpoints |
  | `services/api-gateway/requirements.txt` | Added python-jose |
  | `docs/db/schema.sql` | Added users table |
  | `dashboard/app/login/page.tsx` | Rewired to real auth service + email field + signup link |
  | `dashboard/app/api/login/route.ts` | Now calls auth-service instead of hardcoded check |
  | `dashboard/app/api/logout/route.ts` | Clears JWT cookie |
  | `dashboard/app/ClientLayout.tsx` | Added signup + callback to auth pages list |
  | `dashboard/middleware.ts` | Added /signup and /auth/callback to public paths |
  | `dashboard/lib/api.ts` | Sends JWT token from cookie with every API request |
  | `dashboard/app/globals.css` | Added .login-switch styles for signup/login toggle |

  ---

  ## 4. Authentication System — Deep Dive

  ### 4.1 Three Signup Methods

  #### Method 1: Email + Password
  - User fills in name, email, password on `/signup` page
  - Password hashed with **bcrypt** before storage
  - Min 8 characters enforced
  - Returns JWT token immediately
  - Duplicate email returns HTTP 409

  #### Method 2: Google OAuth2
  ```
  User clicks "Google" button
    -> Browser redirects to auth-service /auth/google
    -> auth-service redirects to Google consent screen
    -> User approves, Google sends code back to /auth/google/callback
    -> auth-service exchanges code for access token with Google API
    -> Fetches user email + name + avatar from Google
    -> Creates user in DB (or links to existing account)
    -> Redirects browser to dashboard /auth/callback?token=JWT
    -> Dashboard stores JWT in httpOnly cookie
    -> User lands on /overview, fully authenticated
  ```

  #### Method 3: GitHub OAuth2
  Same flow as Google but with GitHub's OAuth endpoints. Also fetches the user's verified primary email (handles private emails).

  ### 4.2 Account Linking
  If you sign up with email first, then later click "Google" with the same email, the accounts merge. No duplicate users.

  ### 4.3 JWT Token (24h validity)
  ```json
  {
    "sub": "42",           // user ID in our database
    "email": "user@co.com",
    "role": "viewer",      // viewer | analyst | admin
    "exp": 1743638400,     // expiry timestamp
    "iat": 1743552000      // issued at
  }
  ```

  ### 4.4 Security Flow
  ```
  Browser cookie (httpOnly) -> Next.js server reads cookie -> sends as
  Authorization: Bearer <token> header -> API Gateway verifies JWT
  signature + expiry -> allows/denies request
  ```

  The cookie is `httpOnly` (JavaScript can't read it = no XSS theft) and `sameSite: lax` (no CSRF from other domains).

  ---

  ## 5. Dashboard Signup/Login — Frontend Integration

  ### 5.1 What the User Sees

  **Login Page** (`/login`):
  - Email + password form (was username, now email)
  - "Sign In" button -> calls auth-service /auth/login
  - "Google" button -> redirects to Google OAuth flow
  - "GitHub" button -> redirects to GitHub OAuth flow
  - "Don't have an account? **Sign Up**" link at bottom

  **Signup Page** (`/signup`):
  - Full name, email, password, confirm password form
  - Client-side validation (password match, min 8 chars)
  - "Sign Up" button -> calls auth-service /auth/signup
  - "Google" button -> redirects to Google OAuth flow
  - "GitHub" button -> redirects to GitHub OAuth flow
  - "Already have an account? **Sign In**" link at bottom

  **OAuth Callback** (`/auth/callback`):
  - Shows "Completing sign in..." spinner
  - Stores the JWT token from URL params into httpOnly cookie
  - Redirects to `/overview` on success
  - Shows error + "Back to login" link on failure

  ### 5.2 How API Calls Now Work

  Before (Phase 3):
  ```
  fetch('http://localhost:8000/sla-risk')   // no auth, open to anyone
  ```

  After (Phase 4):
  ```
  // lib/api.ts reads the auth_token cookie server-side
  const token = cookies().get('auth_token')?.value;
  fetch('http://localhost:8000/sla-risk', {
    headers: { Authorization: `Bearer ${token}` }
  });
  ```

  Every page that fetches data automatically includes the JWT. If the token is missing or expired, the API returns 401 and the middleware redirects to `/login`.

  ---

  ## 6. GitHub Actions CI/CD — Full Explanation

  ### 6.1 What is GitHub Actions?

  GitHub Actions is GitHub's built-in CI/CD system. It runs automated workflows on GitHub's servers whenever code changes happen. You don't need to install anything — it's already available on every GitHub repository.

  The workflow is defined in a YAML file at `.github/workflows/ci-cd.yml`. GitHub reads this file and knows what to do.

  ### 6.2 When Does It Run?

  The pipeline triggers automatically on:
  - **Every push to `main` branch** — full pipeline including deploy
  - **Every push to `dev` branch** — full pipeline except deploy
  - **Every Pull Request to `main`** — full pipeline except deploy (images not pushed)

  **You don't need to do anything to launch it.** Just push your code:
  ```bash
  git add .
  git commit -m "my changes"
  git push origin dev
  ```
  GitHub sees the push, reads `.github/workflows/ci-cd.yml`, and starts running the pipeline. You can watch it live at:
  ```
  https://github.com/<your-username>/telecom-cloud-intelligence/actions
  ```

  ### 6.3 The 6 Stages — What Each One Does

  ```
  PUSH CODE
      |
      v
  [Stage 1: LINT] -----> checks code quality (ruff)
      |
      v
  [Stage 2: TEST] -----> runs pytest with a real PostgreSQL
      |
      v
  [Stage 3: BUILD] ----> builds Docker images, pushes to registry
      |
      +------+------+
      |             |
      v             v
  [Stage 4:     [Stage 5:
  INTEGRATION]   SECURITY]
      |             |
      +------+------+
            |
            v
  [Stage 6: DEPLOY] ---> only on main branch
  ```

  #### Stage 1: Lint & Format Check
  **What it does:** Checks that your Python code follows coding standards.
  **Tool:** `ruff` (a fast Python linter, like a spell-checker for code)
  **How:** Runs in parallel on all 4 services (api-gateway, ai-service, pipeline-worker, auth-service)
  **What it catches:** Unused imports, undefined variables, wrong formatting, style issues
  **If it fails:** Your code has style/quality issues. Fix them and push again.

  #### Stage 2: Unit Tests
  **What it does:** Runs all automated tests to verify the code works correctly.
  **Tool:** `pytest` with code coverage reporting
  **How:** For each service, GitHub spins up a temporary PostgreSQL 16 database, installs the service's Python dependencies, and runs any tests in the `tests/` directory.
  **Environment:** Each service gets its own isolated database.
  **If it fails:** A test detected a bug. Read the error output, fix the code, push again.
  **Note:** If a service has no `tests/` directory yet, it skips gracefully with a note.

  #### Stage 3: Build Docker Images
  **What it does:** Builds the Docker container for each service and pushes it to GitHub Container Registry (GHCR).
  **Tool:** Docker Buildx (optimized builder)
  **Tags applied to each image:**
  - Branch name (`dev`, `main`)
  - Git commit SHA (e.g., `d82d1a5`)
  - `latest` (only for main branch)
  **Where images go:** `ghcr.io/<your-username>/telecom-cloud-intelligence/<service-name>`
  **Caching:** Uses GitHub Actions cache so rebuilds are fast (only changed layers rebuild).
  **On PRs:** Images are built (to verify they compile) but NOT pushed to the registry.

  #### Stage 4: Integration Test
  **What it does:** Starts the ENTIRE platform (all 8 Docker containers) and tests everything works together end-to-end.
  **How it works:**
  1. Runs `docker compose up --build -d` on the GitHub runner
  2. Waits up to 2.5 minutes for all services to become healthy
  3. Tests health endpoints (api-gateway, ai-service, auth-service)
  4. Runs a complete signup flow:
    - Creates a user account via POST /auth/signup
    - Logs in with the same credentials via POST /auth/login
    - Fetches the user profile via GET /auth/me with the JWT
    - Accesses a protected API endpoint with the JWT
    - Verifies that requests WITHOUT a token get HTTP 401 (rejected)
  5. If anything fails, collects all container logs for debugging
  6. Tears down all containers and volumes when done

  **This is the most important stage** — it proves the entire system works as a unit, not just individual services.

  #### Stage 5: Security Scan
  **What it does:** Checks all Python dependencies for known security vulnerabilities (CVEs).
  **Tool:** `pip-audit` (scans requirements.txt against vulnerability databases)
  **Also checks:** Scans source code for accidentally hardcoded passwords/secrets.
  **Runs in parallel** with the integration test (they're independent).

  #### Stage 6: Deploy
  **When it runs:** ONLY on pushes to `main` branch (not dev, not PRs)
  **What it does:** Currently outputs deployment instructions. In the future, this would:
  - Pull the freshly-built images from GHCR
  - Deploy them to production (Docker Compose or Huawei Cloud Stack)
  - Run database migrations
  **Requires:** GitHub environment "production" approval (a human must click "approve" in the GitHub UI before it runs)

  ### 6.4 How to Set It Up on GitHub

  1. **Push the repo to GitHub** (if not already):
    ```bash
    git remote add origin https://github.com/<you>/telecom-cloud-intelligence.git
    git push -u origin main
    git push -u origin dev
    ```

  2. **That's it.** GitHub Actions is enabled by default. The moment you push, the workflow starts.

  3. **To see the pipeline running:**
    - Go to your repo on GitHub
    - Click the **"Actions"** tab at the top
    - You'll see the workflow running with all 6 stages

  4. **Green checkmark** = all stages passed. **Red X** = something failed (click to see which stage and read the error).

  5. **On Pull Requests:** When you create a PR from `dev` to `main`, the pipeline runs on the PR. The PR page will show "All checks passed" or "Some checks failed" — reviewers can see if the code is safe to merge.

  ### 6.5 How to View Pipeline Results

  **From terminal:**
  ```bash
  # List recent pipeline runs
  gh run list --workflow=ci-cd.yml

  # View details of a specific run
  gh run view <run-id>

  # Watch a running pipeline live
  gh run watch
  ```

  **From GitHub website:**
  - Repository -> Actions tab -> Click on any run -> See each stage's logs

  ### 6.6 What Tests Does It Run? (Summary)

  | Test | What It Verifies |
  |------|-----------------|
  | Ruff lint | Code quality, no syntax errors, clean imports |
  | Ruff format | Consistent code formatting |
  | pytest | Unit tests pass (when tests/ exist) |
  | Docker build | Each service compiles into a valid container |
  | Health check | All 3 HTTP services respond on their ports |
  | Signup flow | User registration creates account + returns JWT |
  | Login flow | Credentials return valid JWT token |
  | Auth/me | JWT token resolves to correct user profile |
  | Protected access | JWT grants access to analytics endpoints |
  | Auth rejection | Requests without JWT get 401 Unauthorized |
  | pip-audit | No known CVEs in Python dependencies |
  | Secret scan | No hardcoded passwords in source code |

  ---

  ## 7. Updated Architecture

  ### Service Map (8 containers)

  ```
                            +------------------+
                            |   Dashboard      |
                            |   (Next.js)      |
                            |   :3001          |
                            +--------+---------+
                                    |
                      +--------------+--------------+
                      |                              |
                      v                              v
            +----------------+            +------------------+
            | Auth Service   |            |   API Gateway    |
            | :8002          |            |   :8000          |
            | signup/login   |            |   JWT verified   |
            | Google OAuth   |  JWT token |   6 endpoints    |
            | GitHub OAuth   |----------->|                  |
            +-------+--------+            +--------+---------+
                    |                              |
                    v                              v
            +----------------+            +------------------+
            |  PostgreSQL    |            |   AI Service     |
            |  :5432         |            |   :8001          |
            |  8 tables      |            |   3 ML models    |
            +----------------+            +------------------+
                                                    ^
            +----------------+            +--------+---------+
            |    MinIO       |            | Pipeline Worker  |
            |  :9000/9001    |            | 22-step daemon   |
            |  3-layer lake  |            | every 2 minutes  |
            +----------------+            +------------------+

            +----------------+            +------------------+
            |  Prometheus    |            |    Grafana       |
            |  :9090         |            |    :3000         |
            +----------------+            +------------------+
  ```

  ---

  ## 8. Database Schema Changes

  ### New Table: `users`

  ```sql
  CREATE TABLE users (
      id            BIGSERIAL PRIMARY KEY,
      email         TEXT NOT NULL UNIQUE,
      password_hash TEXT,                       -- NULL for OAuth-only users
      full_name     TEXT,
      avatar_url    TEXT,
      provider      TEXT NOT NULL DEFAULT 'local',  -- 'local'|'google'|'github'
      provider_id   TEXT,                       -- OAuth provider's user ID
      role          TEXT NOT NULL DEFAULT 'viewer',  -- 'viewer'|'analyst'|'admin'
      is_active     BOOLEAN NOT NULL DEFAULT TRUE,
      created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE(provider, provider_id)
  );
  ```

  **Indexes:**
  - `idx_users_email` -- fast email lookups for login
  - `idx_users_provider` -- fast OAuth provider+ID lookups

  ### Complete Table Count: 8

  | # | Table | Purpose | New? |
  |---|-------|---------|------|
  | 1 | `users` | User accounts & OAuth profiles | **YES** |
  | 2 | `pipeline_runs` | Pipeline execution metadata | No |
  | 3 | `dataset_registry` | Data lake object catalog | No |
  | 4 | `model_registry` | ML model artifact versions | No |
  | 5 | `sla_risk_scores` | GBR risk predictions | No |
  | 6 | `anomalies` | OSS anomaly detections | No |
  | 7 | `revenue_anomalies` | BSS revenue anomaly detections | No |
  | 8 | `correlation_insights` | OSS-BSS correlation results | No |

  ---

  ## 9. How to Use Everything

  ### 9.1 Start the Platform
  ```bash
  docker compose up --build -d
  ```
  This starts **8 containers** including auth-service on port 8002.

  ### 9.2 Use the Dashboard
  1. Open `http://localhost:3001` in your browser
  2. You'll be redirected to the **Login** page
  3. Click **"Sign Up"** at the bottom to create an account
  4. Fill in name, email, password -> click "Sign Up"
  5. You're now logged in and can see all dashboards

  ### 9.3 Sign Up via API (for testing)
  ```bash
  curl -X POST http://localhost:8002/auth/signup \
    -H "Content-Type: application/json" \
    -d '{"email":"souhayl@telecom.tn","password":"MyPass123!","full_name":"Souhayl"}'
  ```

  ### 9.4 Enable Google/GitHub OAuth

  **For Google:**
  1. Go to https://console.cloud.google.com/apis/credentials
  2. Create an OAuth 2.0 Client ID
  3. Set Authorized redirect URI to: `http://localhost:8002/auth/google/callback`
  4. Copy Client ID and Client Secret

  **For GitHub:**
  1. Go to https://github.com/settings/developers
  2. Click "New OAuth App"
  3. Set Authorization callback URL to: `http://localhost:8002/auth/github/callback`
  4. Copy Client ID and Client Secret

  **Then start with env vars:**
  ```bash
  export GOOGLE_CLIENT_ID="your-id"
  export GOOGLE_CLIENT_SECRET="your-secret"
  export GITHUB_CLIENT_ID="your-id"
  export GITHUB_CLIENT_SECRET="your-secret"
  export JWT_SECRET="a-strong-random-secret"
  docker compose up --build -d
  ```

  ### 9.5 CI/CD Pipeline
  Just push code to GitHub. The pipeline runs automatically:
  ```bash
  git push origin dev     # runs lint -> test -> build -> integration -> security
  git push origin main    # same + deploy stage
  ```
  Watch it at: `https://github.com/<you>/telecom-cloud-intelligence/actions`

  ---

  ## 10. What Comes Next (Phase 5-6)

  ### Phase 5 — Production Hardening
  | Task | Description |
  |------|-------------|
  | Email verification | Require email confirmation after signup |
  | Password reset | Forgot-password flow with email token |
  | Rate limiting | Prevent brute-force login attempts |
  | Refresh tokens | Short-lived access + long-lived refresh tokens |
  | RBAC enforcement | Admin-only endpoints, analyst write access |
  | HTTPS/TLS | TLS termination at gateway level |

  ### Phase 6 — HCS Deployment
  | Task | Description |
  |------|-------------|
  | Huawei SWR | Push Docker images to Software Repository |
  | CCE deployment | Kubernetes manifests for Cloud Container Engine |
  | RDS PostgreSQL | Migrate to managed database |
  | OBS storage | Replace MinIO with Object Storage Service |
  | IAM integration | Map platform roles to Huawei Cloud IAM |

  ---

  ## Technology Summary

  | Component | Technology | Version |
  |-----------|-----------|---------|
  | Auth Service | FastAPI + python-jose + passlib | 1.0 |
  | Password Hashing | bcrypt (via passlib) | - |
  | Token Format | JWT (HS256, 24h) | - |
  | OAuth2 Providers | Google, GitHub | - |
  | Dashboard | Next.js 14, React 18 | 14.2.5 |
  | CI/CD | GitHub Actions | v4 |
  | Container Registry | GHCR | - |
  | Linter | ruff | latest |
  | Security Scanner | pip-audit | latest |
  | Test Framework | pytest | latest |

  ---

  *Phase 4 complete.*
  *Platform: 4 microservices + 1 dashboard + 3 infrastructure services = 8 containers.*
  *Database: 8 tables. API endpoints: 15. Auth methods: 3.*
  *CI/CD: 6 stages, 12 automated checks, fully triggered on push.*
