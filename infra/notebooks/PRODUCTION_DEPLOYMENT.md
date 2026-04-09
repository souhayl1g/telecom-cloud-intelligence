# Production Deployment Guide
# Telecom Cloud Intelligence — Automated Pipeline

## Quick Start

### 1. Build and Start with Auto-Pipeline

```bash
# Set environment variable
export AUTO_PIPELINE=true

# Build and start all services
docker compose up --build -d

# Watch pipeline logs
docker compose logs -f notebooks
```

### 2. Verify Pipeline Execution

```bash
# Check pipeline status
docker compose exec notebooks cat /app/logs/pipeline_*.log | tail -50

# Check Jupyter is running
curl http://localhost:8888/api
```

## Architecture

```
Container Startup Sequence
├── 1. Entrypoint.sh (AUTO_PIPELINE check)
│   ├── If AUTO_PIPELINE=true
│   │   └── Run pipeline_runner.py in background
│   │       ├── Health checks (DB, MinIO, AI service)
│   │       ├── Generate synthetic data
│   │       ├── Run AI inference
│   │       └── Upload results to MinIO
│   └── Always start Jupyter server
└── 2. Jupyter Notebook Server (port 8888)
```

## Startup Time Budget (120s)

| Phase | Time | Description |
|-------|------|-------------|
| Container init | 5s | Environment setup, log files |
| Health checks | 10s | DB, MinIO, AI service |
| Data generation | 5s | OSS + BSS synthetic data |
| AI inference | 30s | SLA risk, anomaly detection |
| Data persistence | 10s | MinIO upload, DB write |
| **Total** | **~60s** | Well within 120s budget |

## Error Handling

### Retry Logic
- Database connection: 3 retries with exponential backoff
- MinIO operations: 3 retries with 2s initial delay
- AI service calls: 3 retries with 2s initial delay

### Idempotency
- Lock file prevents duplicate runs
- 5-minute stale lock cleanup
- Safe to re-run on failure

### Timeout
- Pipeline killed after 120s (configurable)
- Graceful shutdown with SIGTERM
- Exit code 3 on timeout

## Monitoring

### Health Checks

```bash
# PostgreSQL
docker compose exec postgres pg_isready -U telecom

# MinIO
docker compose exec minio mc ls local/

# AI Service
curl http://localhost:8001/health

# Pipeline logs
docker compose logs notebooks | grep -E "\[pipeline\]|\[INFO\]|\[ERROR\]"
```

### Metrics

Pipeline outputs structured JSON logs for monitoring:
```json
{
  "timestamp": "2026-04-08T12:00:00Z",
  "level": "INFO",
  "step": "DATA_GENERATION",
  "message": "Step completed",
  "duration": 4.23
}
```

## Production Checklist

- [ ] Set `AUTO_PIPELINE=true`
- [ ] Set `PIPELINE_TIMEOUT=120` (or higher for slow environments)
- [ ] Verify `JWT_SECRET` is strong and unique
- [ ] Configure external PostgreSQL (RDS) for production
- [ ] Configure external object storage (OBS/S3) for production
- [ ] Set up log aggregation (Prometheus, Grafana)
- [ ] Configure resource limits in docker-compose

## Troubleshooting

### Pipeline Times Out

Increase timeout:
```bash
export PIPELINE_TIMEOUT=180
docker compose up -d notebooks
```

### Pipeline Fails with "Dependency unavailable"

Check dependencies are healthy:
```bash
docker compose ps
docker compose logs postgres minio ai-service
```

### Jupyter Token Not Working

Generate new token:
```bash
docker compose exec notebooks python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then restart with new token:
```bash
export JUPYTER_TOKEN=<new-token>
docker compose up -d notebooks
```

## Scaling

For high-volume scenarios:

1. Increase pipeline timeout
2. Run pipeline in separate service (notebooks)
3. Use dedicated ML inference service
4. Scale PostgreSQL with read replicas
