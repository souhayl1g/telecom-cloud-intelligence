---
name: nexo-hcs-deployer
description: Deploy Telecom NeXoligence to Huawei Cloud Stack (HCS). Use when: (1) mapping local services to HCS equivalents, (2) pushing Docker images to SWR, (3) configuring OBS buckets, (4) setting up RDS for PostgreSQL, (5) creating ECS task definitions, (6) collecting deployment evidence screenshots, (7) documenting HCS architecture for defense.
---

# NeXo HCS Deployer

Deploy the entire NeXo platform to Huawei Cloud Stack with evidence collection.

## Service Mapping

| Local | HCS Service | Mapping Notes |
|---|---|---|
| Docker containers | ECS (Elastic Cloud Server) / CCE (Cloud Container Engine) | Push images to SWR first |
| MinIO | OBS (Object Storage Service) | Update S3_ENDPOINT env var |
| PostgreSQL 16 | RDS for PostgreSQL / GaussDB | Update DATABASE_URL env var |
| Docker network | VPC | Create private subnet |
| Env secrets | IAM / KMS | Use HCS secret manager |
| Ollama/Qwen3:8b | ModelArts / EI | Swap API endpoint in orchestrator.py |

## Deployment Steps

### 1. Push Images to SWR

```bash
# Login to SWR
docker login -u {AK} -p {SK} swr.{region}.myhuaweicloud.com

# Tag and push each service
for svc in api-gateway ai-service auth-service pipeline-worker agent-service dashboard; do
  docker tag telecom-cloud-intelligence-$svc:latest \
    swr.{region}.myhuaweicloud.com/{project}/$svc:latest
  docker push swr.{region}.myhuaweicloud.com/{project}/$svc:latest
done
```

### 2. Configure OBS

```bash
# Create buckets
obscmd mb obs://nexo-raw
obscmd mb obs://nexo-processed
obscmd mb obs://nexo-curated

# Update ai-service + pipeline-worker env:
# S3_ENDPOINT=https://obs.{region}.myhuaweicloud.com
# S3_ACCESS_KEY={AK}
# S3_SECRET_KEY={SK}
```

### 3. Create RDS Instance

- Engine: PostgreSQL 16
- Instance type: minimum 2 vCPU / 4GB RAM
- Storage: 100GB SSD
- VPC: same as ECS tasks
- Apply schema: `docs/db/schema.sql`

### 4. ECS Task Definitions

Create task definition per service:
- **api-gateway**: 1 vCPU, 2GB RAM, port 8000, public ALB
- **ai-service**: 2 vCPU, 4GB RAM, port 8001, internal ALB
- **pipeline-worker**: 1 vCPU, 2GB RAM, no exposed port
- **dashboard**: 1 vCPU, 2GB RAM, port 3001, public ALB

### 5. Evidence Collection

For defense, collect screenshots of:
- [ ] SWR repository with all 5+ images
- [ ] OBS console showing 3 buckets
- [ ] RDS instance running PostgreSQL 16
- [ ] ECS task definitions and running tasks
- [ ] VPC network topology
- [ ] Health endpoint response from deployed api-gateway

## HCS Architecture Document

Write to `docs/deployment/hcs-mapping.md`:
- Exact service mappings
- Environment variable changes
- Network topology diagram
- Cost estimates
- Security group rules

## Key Files

- `docs/deployment/hcs-mapping.md` — HCS deployment guide
- `docs/deployment/local-docker.md` — Local reference
- `docker-compose.yml` — Base for ECS task definitions
