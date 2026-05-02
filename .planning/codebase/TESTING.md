# TESTING.md — Telecom Cloud Intelligence

> Test structure and practices
> Mapped: 2026-04-25

---

## Summary

**No unit or integration tests exist** in this codebase. Test infrastructure is referenced in CI but never invoked.

---

## Current State

### Python services
- `services/*/tests/` directories: **absent** in all 4 services
- `pytest` and `pytest-cov` installed in CI environment but never run
- CI stage 2 (test): checks for `tests/` directory, skips with message:
  ```
  No tests directory found — skipping (tests should be added)
  ```

### Dashboard
- No test framework installed (`package.json` devDependencies has no jest/vitest/testing-library)
- No test scripts in `package.json`
- No `__tests__/` or `*.test.ts` files

---

## CI Integration Testing (Stage 4)

The only automated testing is a Docker Compose integration smoke test in `.github/workflows/ci-cd.yml`:

```yaml
# Stage 4: Integration
- name: Wait for services
  run: |
    docker compose up -d
    sleep 30
    curl -f http://localhost:8000/health
    curl -f http://localhost:8001/health
    curl -f http://localhost:8002/health
```

Tests: service liveness only. No data assertions.

### CI Test Database
PostgreSQL 16 provisioned in CI with:
- DB: `telecom_intel_test`
- User/pass: same as dev defaults
- Used only for integration smoke test

---

## Security Scanning (Stage 5)

```yaml
- run: pip-audit -r requirements.txt
- run: safety check -r requirements.txt
```

Runs on all 3 Python services. No SAST/DAST.

---

## What Should Exist (Gaps)

### Python unit tests needed
```
services/api-gateway/tests/
  test_sla_risk.py       # Test /sla-risk endpoint
  test_anomalies.py      # Test /anomalies endpoint
  test_actions.py        # Test L4 agent CRUD

services/ai-service/tests/
  test_infer.py          # Test /infer/* endpoints
  test_model_reload.py   # Test /models/reload

services/auth-service/tests/
  test_auth.py           # Test login/signup/oauth flow
```

### Dashboard tests needed
```
dashboard/__tests__/
  components/            # React component tests (vitest + testing-library)
  api/                   # API route tests (Next.js test utils)
```

### Missing test patterns
- No mock for psycopg2 (tests would need real DB or connection mock)
- No fixture for JWT tokens in tests
- No model inference mocking for ai-service tests

---

## Recommended Test Stack

| Layer | Tool |
|-------|------|
| Python unit | pytest + pytest-cov |
| Python API | pytest + httpx (async ASGI client) |
| DB mocking | pytest-postgresql or docker-based fixture |
| Dashboard | vitest + @testing-library/react |
| E2E | Playwright (future) |

---

## Coverage Baseline

Current coverage: **0%** (no tests).

CI enforces: nothing (no coverage gate configured).
