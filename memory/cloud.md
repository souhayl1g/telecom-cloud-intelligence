# Cloud & Infrastructure Memory

> Last updated: 2026-04-29

## Docker Services

All services orchestrated via docker-compose.yml with 15+ containers.

### Core Services

| Service | Port | Image | Status |
|---------|------|-------|--------|
| postgres | 5432 | postgres:16 | Running |
| minio | 9000/9001 | minio/minio | Running |
| api-gateway | 8000 | telecom-cloud-intelligence/api-gateway | Running |
| ai-service | 8001 | telecom-cloud-intelligence/ai-service | Fixed build (local torch wheel) |
| auth-service | 8002 | telecom-cloud-intelligence/auth-service | Running |
| agent-service | 8003 | telecom-cloud-intelligence/agent-service | Running |
| dashboard | 3001 | telecom-cloud-intelligence/dashboard | Running |
| pipeline-worker | — | telecom-cloud-intelligence/pipeline-worker | Daemon mode |

### Observability Stack (SigNoz)

| Service | Port | Status |
|---------|------|--------|
| signoz-frontend | 3301 | Running |
| otel-collector | 4317/4318 | Running |
| clickhouse | — | Internal |

### Docker Build Fix (2026-04-29)

**Problem:** ai-service Docker build timed out downloading torch (~200MB wheel at 250KB/s).

**Solution:**
1. Pre-downloaded `torch-2.5.1+cpu-cp311-cp311-linux_x86_64.whl` (174.7 MB) locally
2. COPY wheel into Docker build context
3. `pip install /tmp/torch-2.5.1+cpu-cp311-cp311-linux_x86_64.whl`
4. Used `--no-deps xgboost==2.1.4` to skip 300MB nvidia-nccl GPU dependency

**Result:** Build completes in ~4 minutes, image size 5.01GB.

### HCS Deployment Mapping

| Local | Huawei Cloud Stack |
|-------|-------------------|
| Docker containers | ECS / CCE |
| MinIO volumes | OBS (Object Storage Service) |
| PostgreSQL | RDS for PostgreSQL |
| Docker network | VPC |
| Env secrets | IAM / KMS |
| Ollama | ModelArts / EI |

### Commands

```bash
make start-NeXo     # Start everything
make start-dev      # Dev mode (no auto-pipeline)
make stop           # Stop all
make restart        # Restart
make svc-health     # Health check
make logs [service] # View logs
make db-shell       # PostgreSQL shell
make db-reset       # Reset DB (WARNING)
make db-backup      # Backup DB
make pipeline-logs  # Pipeline execution logs
make test-pipeline  # Manual pipeline run
```
