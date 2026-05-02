# Codebase Concerns

**Analysis Date:** 2026-04-25

---

## Tech Debt

**No DB connection pooling — new connection per request:**
- Issue: Every API endpoint calls `psycopg2.connect()` directly inside a `@contextmanager`. Under concurrent load, this opens/closes a fresh TCP connection for every HTTP request.
- Files: `services/api-gateway/main.py` (line 70–88), `services/auth-service/main.py` (line 81–97), `services/pipeline-worker/worker/__main__.py` (line 47–51)
- Impact: Latency spikes under load; PostgreSQL max_connections exhausted if multiple pipeline runs overlap with dashboard usage; no connection reuse.
- Fix approach: Replace `get_conn()` + `_db()` with `psycopg2.pool.ThreadedConnectionPool` or switch to `asyncpg` with an async pool. SQLAlchemy with `create_engine(pool_size=10)` is the lowest-friction migration path.

**ML model metrics hardcoded in API route — not live from DB:**
- Issue: `/api/model-metrics` in the dashboard returns a static TypeScript object with training metrics last updated 2026-04-08. It does not query the `model_registry` table or re-read the `.joblib` files.
- Files: `dashboard/app/api/model-metrics/route.ts` (entire file, 98 lines, all static)
- Impact: After model retraining, the Model Evaluation page silently shows stale metrics with no staleness indicator. The `pb-model-retrain` playbook can hot-reload models but metrics in the UI remain frozen.
- Fix approach: Store evaluation metrics in `model_registry` as a JSONB column. Have `ai-service` return metrics from `/models/reload`. Fetch dynamically from `api-gateway` via a new `/model-metrics` endpoint.

**Pipeline worker: single-threaded daemon with no concurrency guard:**
- Issue: `run_once()` runs every 120 seconds with `time.sleep(120)`. No file lock, no DB advisory lock, no PID file. If the container restarts mid-run, a new instance can start before the previous one's `finished_at` is written, leaving orphaned `status='started'` rows.
- Files: `services/pipeline-worker/worker/__main__.py` (lines 859–872)
- Impact: Duplicate `run_id` conflicts are guarded by `UNIQUE(run_id)` but concurrent writes to `anomalies` / `sla_risk_scores` from two overlapping runs can produce duplicate data for the same window. The `error_message` truncation at 500 chars (line 576) also silently drops long tracebacks.
- Fix approach: Use a PostgreSQL advisory lock (`pg_try_advisory_lock`) at the start of `run_once()` to guarantee single execution across restarts. Or use a proper scheduler (APScheduler with job coalescing).

**Recharts pinned to v2.15.3 — upgrade blocked indefinitely:**
- Issue: Recharts is pinned at `2.15.3` in `dashboard/package.json`. v3.x causes React error #310 (non-serializable objects through reconciliation). This is a known upstream breaking change.
- Files: `dashboard/package.json`
- Impact: Security patches in Recharts v3+ cannot be adopted. Any team member running `npm update` without reading the lock file will break the dashboard at runtime with a cryptic React error.
- Fix approach: Add an `overrides` block in `package.json` with a comment explaining the pin. Consider migrating to a maintained alternative (e.g., Visx, Nivo) as a future phase.

**Synthetic data hardcoded in pipeline — `region="demo"`, `seed=42`:**
- Issue: `generate_oss()` defaults to `seed=42` and `region="demo"`. The daemon loop derives `run_seed` from `run_id` hash (good) but `region` is hardcoded as `"demo"` in `run_once()` (line 550) with no env-var override.
- Files: `services/pipeline-worker/worker/__main__.py` (lines 550, 79–80)
- Impact: All pipeline data in the DB has `region="demo"`, making multi-region queries and topology overlays always return mock data. Phase 3.5 real-data ingestion will need to replace this entirely.
- Fix approach: Add `PIPELINE_REGION` env var. Move synthetic data generation behind a `DATA_MODE=synthetic|real` switch.

**Agent-service and data-ingest excluded from CI pipeline:**
- Issue: `.github/workflows/ci-cd.yml` only tests `[api-gateway, ai-service, pipeline-worker, auth-service]`. The `agent-service` (Phase 3.5+) and `data-ingest` services are built via `docker-compose.yml` but never linted, tested, or built in CI.
- Files: `.github/workflows/ci-cd.yml` (lint/test/build matrix, lines ~15–120)
- Impact: Any Python syntax error or broken import in `services/agent-service/` or `services/data-ingest/` will only surface at `docker compose up` time, not in PRs.
- Fix approach: Add `agent-service` and `data-ingest` to the CI matrix. Create minimal `tests/` stubs so the "no tests" fallback path passes.

**Ruff format check is `continue-on-error: true` — formatting not enforced:**
- Issue: The lint stage runs `ruff format --check` with `continue-on-error: true` (CI line 44). This means unformatted code never fails a PR.
- Files: `.github/workflows/ci-cd.yml` (line 44)
- Impact: `ruff check` (lint) is enforced but formatting is advisory only. The codebase will drift in style over time.
- Fix approach: Remove `continue-on-error: true` from the format check step.

**No data retention policy — pipeline tables grow unboundedly:**
- Issue: Every 2-minute pipeline run inserts ~200 OSS anomalies + ~200 BSS anomalies + ~10 correlations + 1 SLA score + 1 pipeline run row. There is no DELETE, TRUNCATE, TTL, or partition strategy in `docs/db/schema.sql` or in the pipeline worker.
- Files: `docs/db/schema.sql`, `services/pipeline-worker/worker/__main__.py`
- Impact: At 30 runs/hour, `anomalies` and `revenue_anomalies` accumulate ~6,000 rows/hour (~144K/day). After weeks of operation the query `ORDER BY created_at DESC LIMIT N` on unindexed columns degrades. The `anomalies` and `correlation_insights` tables have no `created_at` index.
- Fix approach: Add `CREATE INDEX idx_anomalies_created ON anomalies(created_at DESC)` and equivalent. Add a nightly cleanup job (e.g., `DELETE FROM anomalies WHERE created_at < NOW() - INTERVAL '7 days'`) or use PostgreSQL table partitioning.

---

## Security Considerations

**JWT secret has a weak, public default in docker-compose:**
- Risk: `JWT_SECRET` defaults to `"telecom-dev-secret-change-in-prod"` in `docker-compose.yml` (lines 40, 63). This string is checked into git and publicly known.
- Files: `docker-compose.yml` (lines 40, 63), `services/api-gateway/main.py` (line 39), `services/auth-service/main.py` (line 53)
- Current mitigation: The fallback only activates if `JWT_SECRET` env var is not set. The variable name suggests awareness.
- Recommendations: Enforce `JWT_SECRET` is required (no default) in production config. Add a startup check that rejects the known-weak default string. Consider rotating to RS256 (asymmetric) to separate signing from verification.

**Internal database password hardcoded in docker-compose (not injected via secrets):**
- Risk: `POSTGRES_PASSWORD: telecom_pw` and MinIO credentials `minio_pw` appear in plaintext in `docker-compose.yml` (lines 7, 24). These are committed to git and visible in container inspect output.
- Files: `docker-compose.yml` (lines 7, 24, 39, 60, 94–97)
- Current mitigation: These are dev-only credentials behind an internal Docker bridge network.
- Recommendations: Move to Docker secrets or `.env` file (gitignored). Use `${POSTGRES_PASSWORD}` env substitution. Provide `.env.example` with placeholder values.

**ClickHouse password hardcoded in docker-compose:**
- Risk: The SigNoz ClickHouse connection string `tcp://admin:27ff0399-0d3a-4bd8-919d-17c2181e6fb9@clickhouse:9000` is committed verbatim in `docker-compose.yml` (line 226).
- Files: `docker-compose.yml` (line 226)
- Current mitigation: ClickHouse is only accessible on the internal Docker network; no external port is exposed.
- Recommendations: Move to `${CLICKHOUSE_PASSWORD}` env substitution. Rotate the credential if this repository has ever been public.

**OAuth state parameter generated but never validated:**
- Risk: Both `google_callback` and `github_callback` accept a `state: str = ""` parameter but never compare it against the originally generated state. The `state` is created at redirect time (lines 293, 367) but not stored in a session or cookie, so the callback cannot verify it.
- Files: `services/auth-service/main.py` (lines 309–354, 378–446)
- Current mitigation: OAuth is optional (empty credentials disable the flow).
- Recommendations: Store the generated state in a short-lived server-side store (Redis or signed cookie) and compare in the callback. Reject mismatched or empty state values.

**JWT passed via OAuth redirect URL query string:**
- Risk: After OAuth login, the auth service redirects to `{FRONTEND_URL}/auth/callback?token={token}&expires_in={expires}` (lines 353, 446). The full JWT is exposed in the URL, which appears in browser history, server access logs, and Referer headers.
- Files: `services/auth-service/main.py` (lines 353, 446)
- Current mitigation: The `/auth/callback` Next.js page reads the token and immediately stores it in an httpOnly cookie via the `/api/login` route.
- Recommendations: Use a short-lived one-time code instead of the full JWT in the redirect URL. The callback exchanges the code for a token server-side.

**No brute-force / rate limiting on `/auth/login` and `/auth/signup`:**
- Risk: The auth service exposes `POST /auth/login` and `POST /auth/signup` with no rate limiting, IP throttling, or lockout after failed attempts.
- Files: `services/auth-service/main.py` (lines 232–253, 208–229)
- Current mitigation: bcrypt hashing (cost factor default ~12) makes each attempt slow (~100ms), providing partial protection.
- Recommendations: Add FastAPI rate-limiting middleware (e.g., `slowapi`) or an nginx rate-limit layer. Implement account lockout after N consecutive failures.

**Internal error details exposed in API responses (`detail=str(e)`):**
- Risk: All 14+ `except Exception as e` blocks in `api-gateway/main.py` return `detail=str(e)` directly to clients. This can leak database error messages, table names, SQL fragments, and internal service URLs.
- Files: `services/api-gateway/main.py` (lines 127, 277, 301, 323, 349, 374, 431, 466, 501, 588, 627, 674, 709, 940)
- Current mitigation: Endpoints require JWT auth, so unauthenticated users cannot trigger these paths.
- Recommendations: Return a generic `"Internal server error"` message to clients. Log `str(e)` server-side only. At minimum, catch `psycopg2.Error` separately and never forward its `pgerror` string.

**Cookies use `sameSite: 'lax'` — not `'strict'`:**
- Risk: Auth cookies are set with `sameSite: 'lax'` in the login route. This allows cookies to be sent on cross-site GET navigations (e.g., links clicked from external pages).
- Files: `dashboard/app/api/login/route.ts` (lines 19, 46, 80)
- Current mitigation: `httpOnly: true` prevents JavaScript access. `secure` is only set in production.
- Recommendations: Use `sameSite: 'strict'` for the auth token cookie. The OAuth callback is the one scenario where `lax` is needed — handle that separately.

---

## Performance Bottlenecks

**Synchronous `requests` library in a FastAPI (async) process:**
- Problem: All inter-service calls in `api-gateway/main.py` use the synchronous `requests` library (lines 141–185, 732–736) inside FastAPI route handlers. FastAPI runs on an async event loop (uvicorn). A blocking `requests.get()` call with `timeout=60` blocks the entire event loop thread.
- Files: `services/api-gateway/main.py` (lines 141, 152, 163, 174, 185, 732)
- Cause: `requests` is not async-compatible. The agent proxy endpoints (`/agent/query`, `/agent/cem`, etc.) block for up to 60 seconds.
- Improvement path: Replace `requests` with `httpx.AsyncClient` and mark route handlers `async def`. This is a drop-in replacement.

**`/api/platform-data` fetches 9 endpoints serially for some paths:**
- Problem: The SSR proxy route fetches platform data. If any upstream endpoint is slow (e.g., Ollama-backed agent calls), the entire dashboard page load is blocked.
- Files: `dashboard/app/api/platform-data/route.ts`
- Cause: Sequential awaits or waterfall fetch patterns.
- Improvement path: Ensure all 9 upstream fetches use `Promise.all()`. Add per-endpoint timeouts with fallback empty values so one slow endpoint doesn't block the page.

**`/infra-stats` runs 6 sequential queries in one request with no caching:**
- Problem: The `GET /infra-stats` endpoint executes 6 separate SQL queries sequentially (row counts across 8 tables, DB size, table sizes, pipeline timing, layer breakdown) on every call.
- Files: `services/api-gateway/main.py` (lines 509–588)
- Cause: No caching layer; `pg_total_relation_size` and `pg_database_size` are catalog lookups that can be slow under write load.
- Improvement path: Cache this response in-memory for 30–60 seconds. Consider a single CTE combining the queries.

---

## Fragile Areas

**`dashboard/app/l4-agent/page.tsx` — 1,461 lines, massive single-file component:**
- Files: `dashboard/app/l4-agent/page.tsx`
- Why fragile: The entire L4 agent UI — chat tab, actions tab, live monitor tab, toast system, action lifecycle, playbook rendering, sparkline charts, donut chart — lives in a single 1,461-line component. `PlatformContext` type uses `any` for 6 of its 8 fields (lines 31–36). State changes anywhere can cause full re-renders of unrelated tabs.
- Safe modification: Isolate changes to the tab currently being modified. The `classifyAction()` function (auto-approve logic) is inline — test its logic carefully before touching it.
- Test coverage: None (no unit tests for action classification or playbook execution logic).

**`execute_action` endpoint — all 5 playbooks in one 230-line function:**
- Files: `services/api-gateway/main.py` (lines 712–940)
- Why fragile: All playbook implementations are `if/elif` branches inside a single endpoint function. The `pb-anomaly-triage` branch reuses the same `cur` cursor that the outer function opened for the action lookup, creating implicit cursor state dependencies. Adding a 6th playbook requires editing this monolith.
- Safe modification: Each playbook branch is self-contained. Test playbook execution via the integration test flow before changing the cursor/connection handling.
- Test coverage: None — playbooks are only exercised via the integration test's signup + action flow.

**OAuth token-in-URL → cookie exchange is a two-hop race:**
- Files: `dashboard/app/auth/callback/page.tsx`, `dashboard/app/api/login/route.ts`
- Why fragile: After OAuth redirect, the callback page reads `?token=` from the URL, then makes a POST to `/api/login` with `action: 'oauth_callback'` to store it in a cookie. If the user refreshes between these two hops (or the POST fails), the token is stranded in the URL with no recovery path.
- Safe modification: Do not change the callback page without understanding the full two-hop flow documented in CLAUDE.md.

**`_ensure_tables()` in auth-service runs on every startup — DDL in hot path:**
- Files: `services/auth-service/main.py` (lines 100–122)
- Why fragile: The `on_startup` handler runs `CREATE TABLE IF NOT EXISTS` including `CREATE INDEX IF NOT EXISTS`. Under concurrent startup (e.g., rolling restarts in Docker Swarm), two instances can race on index creation. Currently harmless because `IF NOT EXISTS` is idempotent, but any future schema migration added here will run twice.
- Safe modification: Move schema management to a dedicated migration tool (Alembic or Flyway) or a one-time init container.

---

## Known Bugs

**Pipeline run `step 1` numbering mismatch in comments:**
- Symptoms: The docstring at the top of `__main__.py` lists step 1 as "Ensure MinIO buckets exist" but the code prints `[2/22] Ensuring MinIO buckets` — step 1 is now "Insert pipeline_runs record" (moved to pre-try block, line 560). The printed step numbers are off by one for the rest of the run.
- Files: `services/pipeline-worker/worker/__main__.py` (lines 1–26, 560–603)
- Trigger: Visible in every pipeline run log.
- Workaround: Cosmetic only — no functional impact.

---

## Dependencies at Risk

**`recharts` v2.15.3 — pinned, cannot receive v3 security patches:**
- Risk: Pinned to a minor release of a major version behind. No active security issue known, but this dependency cannot be upgraded without a significant UI rewrite.
- Impact: Dashboard charts (SLA trend, anomaly history, correlation views).
- Migration plan: Migrate charting to a dependency that doesn't have this breaking-change constraint (Visx, Nivo, or Chart.js with react-chartjs-2). Custom SVG components already exist for the Model Evaluation page — this pattern could be extended.

**`on_event("startup")` FastAPI deprecation:**
- Risk: `@app.on_event("startup")` used in `services/auth-service/main.py` (line 125) is deprecated in FastAPI 0.93+ in favor of `lifespan` context managers.
- Impact: Will produce deprecation warnings in FastAPI 0.115 and will break in a future major version.
- Migration plan: Replace with `@asynccontextmanager` lifespan pattern as documented in FastAPI migration guide.

---

## Test Coverage Gaps

**Zero unit tests across all four CI-tested services:**
- What's not tested: Business logic in all services — JWT creation/validation, playbook execution, ML inference request handling, correlation computation, synthetic data generation.
- Files: `services/api-gateway/`, `services/ai-service/`, `services/auth-service/`, `services/pipeline-worker/`
- Risk: Regressions in core logic (auth, anomaly detection, SLA scoring) are only caught by the integration test, which tests only the happy path (signup → login → `/pipeline-runs`).
- Priority: High — the CI pipeline prints "No tests directory found — skipping" for all four services on every run.

**No TypeScript type checking in CI:**
- What's not tested: Dashboard TypeScript compilation beyond `next build` (which happens only in integration stage). ESLint is not run in CI.
- Files: `.github/workflows/ci-cd.yml`, `dashboard/`
- Risk: `any`-typed API responses (106 occurrences in source files) can mask shape mismatches between API responses and UI expectations. Type errors added in a PR are caught only if a developer runs `tsc --noEmit` locally.
- Priority: Medium — add `npm run type-check` and `npm run lint` steps to the CI lint stage.

**L4 agent action classification logic has no tests:**
- What's not tested: `classifyAction(severity, type, confidence)` function — the auto-approve vs. human-approve decision.
- Files: `dashboard/app/l4-agent/page.tsx` (inline function ~line 100)
- Risk: A logic change (e.g., auto-approving a `remediation` action) would go undetected. This function controls whether real backend operations execute without human review.
- Priority: High — extract to a pure function and add unit tests with Jest.

---

## Scaling Limits

**Ollama on host machine via `host.docker.internal`:**
- Current capacity: Single Qwen2.5:7b instance on local GPU (RTX 3050, 4GB VRAM). One inference at a time.
- Limit: Concurrent L4 agent chat requests queue behind each other. With 60-second timeouts on `/agent/query`, a slow LLM response blocks API gateway worker threads.
- Scaling path: For demo/thesis purposes, current capacity is sufficient. For production, replace with Huawei ModelArts or a dedicated inference server with batching.

**No database migrations system — schema managed manually:**
- Current capacity: Schema applied once via `docs/db/schema.sql` on container init.
- Limit: Any schema change requires manual `ALTER TABLE` or a full volume wipe + reinit. The auth-service `_ensure_tables()` pattern cannot handle `ALTER COLUMN` or index renames.
- Scaling path: Adopt Alembic for Python services. Add a migration runner container in `docker-compose.yml`.

---

*Concerns audit: 2026-04-25*
