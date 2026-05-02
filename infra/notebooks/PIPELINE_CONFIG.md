# Pipeline Configuration
# Telecom NeXoligence — Automated Pipeline

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_PIPELINE` | `false` | Enable pipeline on startup (`true`/`false`) |
| `PIPELINE_MODE` | `oneshot` | Pipeline execution mode (`oneshot`/`daemon`) |
| `PIPELINE_TIMEOUT` | `120` | Max pipeline execution time in seconds |
| `PIPELINE_LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `PIPELINE_IDEMPOTENT` | `true` | Enable idempotency guard |
| `PIPELINE_MAX_RETRIES` | `3` | Max retry attempts per step |
| `PIPELINE_RETRY_DELAY` | `5` | Base delay between retries (seconds) |
| `JUPYTER_PORT` | `8888` | Jupyter server port |
| `JUPYTER_TOKEN` | *(auto)* | Jupyter access token (auto-generated if empty) |

## Usage Examples

### Development (pipeline disabled)
```bash
docker compose up notebooks
```

### Production (pipeline auto-runs)
```bash
AUTO_PIPELINE=true docker compose up -d notebooks
```

### With custom timeout
```bash
AUTO_PIPELINE=true PIPELINE_TIMEOUT=60 docker compose up -d notebooks
```

### Daemon mode (continuous execution)
```bash
AUTO_PIPELINE=true PIPELINE_MODE=daemon docker compose up -d notebooks
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (pipeline disabled or completed) |
| `1` | Pipeline execution failed (after retries) |
| `2` | Dependency unavailable (DB, MinIO) |
| `3` | Pipeline timeout exceeded |
| `4` | Configuration error |

## Log Locations

- Container stdout: Real-time logs
- `/app/logs/pipeline_<timestamp>.log`: Persistent pipeline logs

## Docker Compose Integration

```yaml
notebooks:
  environment:
    AUTO_PIPELINE: ${AUTO_PIPELINE:-false}
    PIPELINE_MODE: ${PIPELINE_MODE:-oneshot}
    PIPELINE_TIMEOUT: ${PIPELINE_TIMEOUT:-120}
    DATABASE_URL: postgresql://telecom:telecom_pw@postgres:5432/telecom_intel
    S3_ENDPOINT: http://minio:9000
    AI_SERVICE_URL: http://ai-service:8001
```
