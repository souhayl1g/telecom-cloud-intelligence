# Dashboard Memory

> Last updated: 2026-04-29

## Architecture

- **Framework:** Next.js 14 App Router + React 18 + TypeScript 5.4.5
- **Styling:** CSS modules + Tailwind-style utilities
- **Charts:** Custom SVG components (Sparkline, DonutChart, RadarChart, ConfusionMatrix, FeatureImportanceChart)
- **Animation:** Framer Motion for page transitions
- **Auth:** JWT via httpOnly cookie, middleware.ts guards routes

## Pages (20+ routes)

| Route | Type | Data Source | Description |
|-------|------|-------------|-------------|
| `/overview` | SSR | API Gateway | Main KPI dashboard with SLA risk, anomalies, correlations |
| `/anomalies` | SSR | API Gateway | OSS + BSS anomaly explorer with heatmap |
| `/vae-anomalies` | Client | `/api/vae-anomalies` | PyTorch VAE anomaly detection results |
| `/sla-risk` | SSR | API Gateway | SLA risk predictor with gauge and trend |
| `/correlations` | SSR | API Gateway | OSS↔BSS convergence heatmap |
| `/intelligence` | SSR | API Gateway | AI Hub — cross-domain root cause analysis |
| `/predictive` | SSR | API Gateway | Forecasting — linear regression projections |
| `/cem-scores` | Client | `/api/cem-scores` | CEM experience score distribution |
| `/rat-underservice` | Client | `/api/rat-underservice` | RAT underservice detection |
| `/topology` | Client | `/api/platform-data` | Network topology SVG map |
| `/capacity` | SSR | API Gateway | Capacity planning with growth projections |
| `/data-warehouse` | SSR | API Gateway | Data catalog and architecture diagram |
| `/pipeline-runs` | SSR | API Gateway | Pipeline audit trail with 14-step visual |
| `/ops-metrics` | Client | `/api/health-check` | System health — 10 service status cards |
| `/model-evaluation` | Client | `/api/model-metrics` | ML governance — 6 model metrics |
| `/l4-agent` | Client | `/api/agent-query` | ADN L4 autonomous agent — 5 tabs |
| `/login` | Client | `/api/login` | Auth with Google/GitHub OAuth |
| `/signup` | Client | `/api/login` | Registration |

## Key Components

- **Sidebar.tsx** — 4-section collapsible nav, L4 Agent CTA
- **CommandPalette.tsx** — `Ctrl+K` fuzzy search across pages + actions
- **RootCauseAnalysis.tsx** — Cross-domain narrative generator
- **AnomalyTimeline.tsx** — Unified OSS+BSS event stream
- **RefreshContext.tsx** — 120s auto-refresh with tab visibility pause

## API Routes

| Route | Methods | Purpose |
|-------|---------|---------|
| `/api/agent-query` | POST | Proxies to agent-service orchestrator |
| `/api/cem-scores` | GET | Direct PostgreSQL CEM queries |
| `/api/chat` | POST | Ollama direct chat proxy |
| `/api/health-check` | GET | 10-service health ping |
| `/api/login` | POST | Multi-action auth (login/signup/oauth) |
| `/api/model-metrics` | GET | Hardcoded real training metrics |
| `/api/platform-data` | GET/POST/PATCH | Universal SSR proxy + action dispatcher |
| `/api/rat-underservice` | GET | Direct PostgreSQL RAT queries |
| `/api/vae-anomalies` | GET | Direct PostgreSQL VAE queries |

## Auth Middleware

- `middleware.ts` guards all routes except `/login`, `/signup`, `/auth/callback`
- Reads `auth_token` httpOnly cookie
- Redirects unauthenticated to `/login`
