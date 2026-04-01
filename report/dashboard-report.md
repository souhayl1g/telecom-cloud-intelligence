# Telecom Cloud Intelligence - Dashboard Report
## L4 Autonomous AI Operations Agent Platform

---

## 1. Executive Summary

This dashboard is the **front-end command center** for an L4 Autonomous AI Operations Agent built for telecom cloud infrastructure. It provides real-time visibility into network operations (OSS), business support systems (BSS), and the autonomous agent's decision-making process.

**Key Capabilities:**
- Real-time SLA breach risk prediction using GradientBoosting ML models
- Anomaly detection across OSS network KPIs and BSS revenue streams using IsolationForest
- OSS-BSS correlation analysis demonstrating O+B convergence
- L4 autonomous agent workspace with approve/reject actions and auto-remediation
- 22-step data pipeline monitoring
- Full observability stack (Prometheus + Grafana)

**Tech Stack:** Next.js 14 (App Router) | TypeScript | Recharts | FastAPI | PostgreSQL | MinIO | Prometheus | Grafana | Docker Compose

---

## 2. Architecture Overview

```
                    +------------------+
                    |   Dashboard      |
                    |  (Next.js :3001) |
                    +--------+---------+
                             |
                    +--------v---------+
                    |   API Gateway    |
                    |  (FastAPI :8000) |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v------+  +----v-------+
     |  PostgreSQL |  | AI Service  |  |   MinIO    |
     |    :5432    |  | (ML :8001)  |  | (S3 :9001) |
     +-------------+  +------+------+  +------------+
                             |
                    +--------v---------+
                    | Pipeline Worker  |
                    | (22-step daemon) |
                    +------------------+
                             |
              +--------------+--------------+
              |                             |
     +--------v--------+      +------------v----+
     |   Prometheus     |      |    Grafana      |
     |     :9090        |----->|     :3000       |
     +------------------+      +-----------------+
```

### Data Flow
1. **Pipeline Worker** runs every cycle: generates/ingests OSS + BSS data, uploads to MinIO
2. Data is processed and fed through **AI Service** (3 ML models)
3. Results persisted to **PostgreSQL** via API Gateway
4. **Dashboard** fetches from API Gateway and renders real-time views
5. **Prometheus** scrapes metrics from API Gateway + AI Service
6. **Grafana** visualizes infrastructure metrics

---

## 3. Dashboard Pages

### 3.1 Login Page (`/login`)
**Purpose:** Authentication entry point to the platform.

**Features:**
- Username/password authentication against environment variables
- Animated background with floating gradient orbs
- Google and GitHub OAuth buttons (UI-ready for future integration)
- Operator Portal SSO button (for future hosting operator integration)
- Success animation on login with smooth redirect
- Session managed via HTTP-only cookies (8-hour expiry)
- All routes are protected by Next.js middleware

**Credentials:** Configured via `AUTH_USER` and `AUTH_PASS` env vars (default: admin/admin)

---

### 3.2 Operations Overview (`/overview`)
**Purpose:** High-level command center showing all critical metrics at a glance.

**Sections:**
| Section | What it shows |
|---------|---------------|
| **KPI Strip** (4 cards) | SLA Risk Score, Total Anomalies, Pipeline Success Rate, Correlations - all clickable, linking to detail pages |
| **L4 Agent Banner** | Live agent status, current health assessment, link to agent workspace |
| **SLA Breach Risk** | RiskGauge component showing current score with Safe/Warning/Critical zones |
| **SLA Risk Trend** | Area chart (Recharts) with historical scores and threshold lines at 0.4 and 0.7 |
| **Anomaly Distribution** | Bar chart breaking down anomalies by severity and domain (OSS vs BSS) |
| **AI Models Status** | Cards for each ML model (SLA Predictor, OSS Anomaly, BSS Revenue) showing version and features |
| **Alert Summary** | Critical/Warning/Low anomaly counts |
| **Pipeline Executions** | Table of recent pipeline runs with status, timing |

**Data Sources:** All 6 API endpoints fetched in parallel (server-side)

---

### 3.3 SLA Risk Analysis (`/sla-risk`)
**Purpose:** Deep dive into SLA breach probability prediction.

**ML Model:** GradientBoostingRegressor with 9 aggregated KPI features

**Sections:**
- **Summary strip:** Current risk, average, peak, lowest, data point count
- **Risk Gauge:** Large visual indicator with color-coded zones
- **Feature Importances:** Bar chart showing which KPI features contribute most to the prediction (when available from API)
- **Risk Trend Chart:** Historical score line with warning/critical thresholds
- **Score History Table:** Full history with score, risk level badge, region, model version, timestamp

**Risk Levels:**
- `< 0.4` = HEALTHY (green)
- `0.4 - 0.7` = WARNING (yellow)
- `> 0.7` = CRITICAL (red)

---

### 3.4 Anomaly Detection (`/anomalies`)
**Purpose:** View all detected anomalies across OSS network and BSS revenue domains.

**ML Model:** IsolationForest (2 instances - one for OSS, one for BSS)

**Sections:**
- **Summary strip:** OSS Critical/Warning/Low counts + BSS Total and High Impact counts
- **Cell Severity Heatmap:** Professional grid showing top 12 cell sites by anomaly concentration, with color-coded severity tiles (low/warning/critical), hover effects, summary bar with legend, and per-cell totals
- **OSS Network Anomalies Table:** Cell ID, KPI name, severity badge, score bar, value vs baseline, region, timestamp
- **BSS Revenue Anomalies Table:** Subscriber, operator, line type (prepaid/postpaid), plan, metric, severity, value, region

---

### 3.5 OSS-BSS Correlation Analysis (`/correlations`)
**Purpose:** Demonstrate O+B convergence by showing statistical correlations between network performance and business metrics.

**Methods:** Pearson and Spearman correlation coefficients

**Sections:**
- **Summary strip:** Total correlations, Pearson count, Spearman count, strong correlations (|r| >= 0.7), statistically significant (p < 0.05)
- **Correlation Heatmap:** Visual grid of Pearson correlation pairs
- **Full Results Table:** Metric X (OSS) vs Metric Y (BSS), method, correlation value, strength label, p-value, significance badge, region

**Strength Classification:**
- `|r| >= 0.7` = Strong
- `|r| >= 0.4` = Moderate
- `|r| >= 0.2` = Weak
- `|r| < 0.2` = Negligible

---

### 3.6 Pipeline Execution History (`/pipeline-runs`)
**Purpose:** Monitor the 22-step data pipeline that powers the entire system.

**Pipeline Stages:**
```
Buckets -> OSS Gen -> BSS Gen -> Upload Raw -> Register ->
Process OSS -> Process BSS -> KPI Agg -> SLA Risk ->
OSS Anomaly -> BSS Anomaly -> Correlate -> Curate -> Persist
```

**Sections:**
- **KPI cards:** Total runs, success rate, failed count, average duration
- **Pipeline Stages visual:** Color-coded flow showing all 14 major steps
- **Run History Table:** Run ID, status (succeeded/failed/running with animated dots), start/finish times, duration, error messages

---

### 3.7 Platform Health (`/ops-metrics`)
**Purpose:** Infrastructure observability and monitoring.

**Sections:**
- **Service Status Cards:** API Gateway (:8000), AI Service (:8001), Prometheus (:9090)
- **Architecture Diagram:** Visual flow showing how metrics flow from services through Prometheus to Grafana
- **Embedded Grafana Dashboard:** Live Grafana iframe showing the `ai-ops-overview` dashboard
- **Direct Links:** Quick access to Grafana and Prometheus UIs

---

### 3.8 L4 Agent Workspace (`/l4-agent`) ★ CORE FEATURE
**Purpose:** The autonomous agent's command center where it presents its decisions, recommendations, and auto-remediation actions for human oversight.

**This is what makes this an L4 system** (TM Forum classification):
- L1 = Manual operations
- L2 = Assisted (AI helps)
- L3 = Conditional (AI recommends, human approves)
- **L4 = Autonomous (AI acts, human oversees)**

**How it works:**
1. The page fetches ALL API data (SLA risk, anomalies, revenue anomalies, correlations, pipelines)
2. An intelligent recommendation engine analyzes the data and generates contextual actions
3. Actions are categorized by type and severity
4. User can expand any action to see details, then approve or reject

**Action Types:**
| Type | Icon | Description |
|------|------|-------------|
| Auto-Remediation | Gear | Agent initiates automatic fixes (load balancing, parameter adjustment, traffic rerouting) |
| Recommendation | Document | Agent suggests actions for human consideration |
| Escalation | Alert triangle | Agent escalates to NOC team for manual intervention |
| Prediction | Activity | Agent reports predictive insights and forecasts |

**Sections:**
- **Agent Status Header:** Active/Processing/Idle indicator + Autonomous/Supervised/Manual mode badge
- **Agent KPIs:** Actions today, auto-remediations, average confidence, uptime
- **Pending Actions:** Interactive cards with severity indicators, confidence scores, expand to see source/impact, approve or reject buttons
- **Executed Actions:** Log of completed actions with confidence scores
- **Rejected Actions:** Dismissed recommendations (lower opacity)
- **Activity Log:** Live console-style output showing agent operations
- **Architecture Section:** TM Forum L1-L4 levels with L4 highlighted + pipeline flow visualization

**Auto-refresh:** Data refreshes every 2 minutes automatically

---

## 4. Navigation & External Links

**Top Navigation Bar** (horizontal, sticky):
| Item | Route | Description |
|------|-------|-------------|
| Overview | `/overview` | Main dashboard |
| SLA Risk | `/sla-risk` | SLA breach prediction |
| Anomalies | `/anomalies` | Anomaly detection |
| Correlations | `/correlations` | OSS-BSS correlation |
| Pipelines | `/pipeline-runs` | Pipeline monitoring |
| Health | `/ops-metrics` | Infrastructure health |
| **L4 Agent** | `/l4-agent` | Agent workspace (highlighted with gold glow) |

**External Links:**
| Link | URL | Purpose |
|------|-----|---------|
| MinIO | `localhost:9001` | Object storage console (raw data, processed files) |
| DWH | `localhost:3000` | Grafana data warehouse dashboard |

**Live Indicator:** Shows seconds since last data refresh, auto-refreshes every 2 minutes

---

## 5. Docker Services

| Service | Port | Image | Purpose |
|---------|------|-------|---------|
| PostgreSQL | 5432 | postgres:16 | Primary data store |
| MinIO | 9000/9001 | minio/minio | S3-compatible object storage |
| API Gateway | 8000 | Custom (FastAPI) | REST API for dashboard |
| AI Service | 8001 | Custom (FastAPI) | ML model inference |
| Pipeline Worker | - | Custom (Python) | 22-step ETL daemon |
| Prometheus | 9090 | prom/prometheus | Metrics collection |
| Grafana | 3000 | grafana/grafana | Metrics visualization |
| Dashboard | 3001 | Next.js (dev) | This dashboard |

**Starting everything:**
```bash
docker compose up -d          # Start all backend services
cd dashboard && npm run dev   # Start dashboard on :3001
```

---

## 6. AI/ML Models

| Model | Algorithm | Features | Purpose |
|-------|-----------|----------|---------|
| SLA Risk Predictor v2.0 | GradientBoostingRegressor | 9 aggregated KPI features | Predicts SLA breach probability (0.0-1.0) |
| OSS Anomaly Detector v2.0 | IsolationForest | 5 KPI features | Detects network anomalies per cell site |
| BSS Revenue Anomaly v2.0 | IsolationForest | Revenue + usage metrics | Detects billing/revenue anomalies per subscriber |

---

## 7. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/sla-risk` | GET | Latest SLA risk score |
| `/sla-risk/history?limit=20` | GET | Historical SLA scores |
| `/anomalies?limit=50` | GET | OSS network anomalies |
| `/revenue-anomalies?limit=50` | GET | BSS revenue anomalies |
| `/correlation?limit=50` | GET | OSS-BSS correlation insights |
| `/pipeline-runs?limit=10` | GET | Pipeline execution history |

---

## 8. Design System

**Theme:** Dark mode with glassmorphism effects
**Colors:**
- Background: `#060911` (deep navy)
- Brand: Purple gradient (`#a78bfa` -> `#6366f1` -> `#4f46e5`)
- Success: `#34d399` (green)
- Warning: `#fbbf24` (yellow)
- Danger: `#f87171` (red)
- Info: `#60a5fa` (blue)
- L4 Agent accent: `#ffd700` (gold)

**Typography:** Inter (UI) + JetBrains Mono (data/code)
**Icons:** Custom SVG vector icons (Lucide-style) throughout - no emoji/pixel icons
**Components:** Cards with backdrop blur, gradient accent borders, animated pulse dots, hover lift effects

---

*Generated: March 2026 | Telecom Cloud Intelligence Platform v2.0*
