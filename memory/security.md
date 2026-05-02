# Security Memory

> Last updated: 2026-04-29

## Authentication

- JWT Bearer tokens for all protected api-gateway endpoints
- Auth service supports: local (bcrypt), Google OAuth, GitHub OAuth
- JWT secret: `telecom-dev-secret-change-in-prod` (MUST change in production)
- OAuth credentials optional for local dev (empty by default)

## Authorization

- `users.role` column: `viewer | analyst | admin`
- Dashboard middleware guards routes
- Future RBAC expansion planned

## Secrets Handling

- No hardcoded passwords in source (enforced by CI secret-scanning)
- All secrets env-var injected
- `.env.local` and `.env.example` present for reference

## CI Security Scan

Stage 5 of CI/CD:
- `pip-audit` on all service requirements.txt
- `safety` check for known vulnerabilities
- Grep-based secret scan for hardcoded password assignments

## Data Confidentiality (CRITICAL)

- `TT_data/` contains real Tunisie Telecom subscriber and network data
- **STRICTLY CONFIDENTIAL**
- Never commit, never export, never share
- All processing must stay local
- `TT_data/` is in `.gitignore` — DO NOT remove

## Network Security

- Docker bridge network isolates services
- API Gateway is the only public-facing service
- Internal services (ai-service, postgres, minio) not exposed externally
- SigNoz observability requires no auth in dev mode

## Default Credentials (Dev Only)

| Service | Username | Password | Database/Bucket |
|---------|----------|----------|-----------------|
| PostgreSQL | telecom | telecom_pw | telecom_intel |
| MinIO | minio | minio_pw | raw, processed, curated |
| JWT Secret | — | telecom-dev-secret-change-in-prod | — |
| ClickHouse | admin | 27ff0399-0d3a-4bd8-919d-17c2181e6fb9 | Internal |
