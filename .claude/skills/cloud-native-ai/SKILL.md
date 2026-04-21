---
name: cloud-native-ai
description: "Cloud-native architecture patterns for AI/ML platforms. Actions: design, improve, optimize, review, refactor, containerize, secure, scale. Elements: FastAPI endpoint, Docker service, docker-compose, PostgreSQL query, MinIO bucket, Prometheus metric, GitHub Actions CI, health check, JWT auth, psycopg2 query, service discovery, data lake layer. Tech: Python 3.11, FastAPI 0.115, PostgreSQL 16, MinIO, Docker, Prometheus, Grafana, GitHub Actions."
---
# Cloud-Native AI Platform Patterns

## This Stack
- **API:** FastAPI 0.115 + psycopg2 (no ORM) + prometheus-fastapi-instrumentator
- **Auth:** JWT Bearer + bcrypt, httpOnly cookies in Next.js
- **Storage:** PostgreSQL 16 (operational) + MinIO 3-layer data lake (raw/processed/curated)
- **Infra:** Docker Compose, 10 services, internal bridge network
- **CI:** GitHub Actions — ruff lint → pytest → docker build → integration → security → deploy

## FastAPI Patterns

### Endpoint Structure
```python
@app.get("/resource")
async def get_resource(limit: int = 50, db=Depends(get_db)):
    # Raw psycopg2, no ORM
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT ... FROM ... WHERE ... LIMIT %s", (limit,))
        return cur.fetchall()
```

### Auth Dependency
```python
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload
```

### Health Check (required for all services)
```python
@app.get("/health")
async def health(): return {"status": "healthy", "service": "api-gateway"}
```

## PostgreSQL Patterns
- Use `%s` placeholders (psycopg2), never f-strings in SQL
- JSONB for ML explanation fields and execution logs
- `ON CONFLICT DO UPDATE` for idempotent inserts
- Always parameterize queries — never concatenate user input

## Docker Patterns
- Base: `python:3.11-slim` for all Python services
- Health check: `HEALTHCHECK CMD curl -f http://localhost:PORT/health`
- Non-root user in production containers
- Secrets via environment variables (never baked into image)
- Multi-stage build if frontend needs to be bundled

## MinIO / Data Lake
- 3 buckets: `raw-data`, `processed-data`, `curated-data`
- Naming: `{service}/{date}/{run_id}/{filename}`
- Always use presigned URLs for temporary access
- HCS mapping: MinIO → OBS (same S3 API, swap endpoint)

## Prometheus Metrics
- `prometheus-fastapi-instrumentator` auto-instruments all routes
- Custom metrics: `Counter`, `Histogram` from prometheus_client
- Scrape config in `infra/monitoring/prometheus.yml`

## CI Rules
- Ruff: `ruff check` + `ruff format --check` before every commit
- Tests: pytest with real DB (no mocks) — integration tests only
- Docker: build all images, run smoke test (`/health` endpoints)
- Security: `pip-audit` + `safety check`

## HCS Cloud Portability
| Local | Huawei Cloud |
|-------|-------------|
| MinIO | OBS (S3-compatible, same boto3 client, change endpoint) |
| PostgreSQL | RDS for PostgreSQL |
| Docker containers | ECS (Elastic Cloud Server) |
| Ollama | ModelArts / EI Enterprise Intelligence |
| Prometheus/Grafana | AOM (Application Operations Management) |

## Common Anti-Patterns to Avoid
- Never use ORM (SQLAlchemy) — raw psycopg2 is intentional for control
- Never commit secrets or TT_data/ (gitignored, confidential)
- Never call :8000 directly from Next.js client — always through `/api/platform-data` SSR proxy
- Never use recharts v3.x — pinned to 2.15.3 (v3 breaks React reconciliation)
