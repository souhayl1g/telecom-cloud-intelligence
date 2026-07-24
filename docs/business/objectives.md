# Business Objectives & Data Science Objectives — NeXo

> CRISP-DM Phase 1 (Business Understanding) + Phase 4 (Modeling) charter.
> Audience: Tunisie Telecom (TT) CTO / Strategic office.
> Owner: Souhayl Guenichi · Last revised: 2026-05-10.

---

## 1. Stakeholder & Pain

| Item | Value |
|---|---|
| Primary stakeholder | TT CTO / Strategic office |
| Secondary | NOC (consumer of L4 actions), Care (downstream beneficiary of CEM intelligence) |
| Defense pain hook | **"Network anomalies are invisible to OSS until a customer complaint reaches Care."** |
| Strategic context | TT is on an ADN (Autonomous Driving Network) maturity journey — the CTO office is funding intelligence layers that close the OSS↔CEM gap and lift autonomy from L2 toward L4. |
| Out-of-scope | HCS migration / cloud portability — reframed as "cloud-native architecture" (microservices + containers + observability), not vendor-mapping. |

---

## 2. Business Objectives

| ID | Objective | Why it matters | Owner |
|---|---|---|---|
| **BO1** | Detect network-induced customer experience degradation **before** the first complaint reaches Care. | Today TT learns about CEM drops via customer calls; intervention happens after damage. Closing the OSS↔CEM gap moves the operator from reactive to predictive. | NOC |
| **BO2** | Lift the ADN autonomy level from L2 to L4 by safely auto-resolving operational actions. | Manual NOC workflows scale poorly. Demonstrating L4-grade auto-approval on info & prediction actions (with audit trail) is a Huawei ADN strategic checkbox. | CTO office |
| **BO3** | Provide a unified OSS+CEM pane of glass that breaks legacy data silos. | OSS dashboards (network) and CEM dashboards (subscriber) live in separate tools. NeXo merges them with statistical convergence (Granger), not just side-by-side widgets. | CTO office |

---

## 3. Data Science Objectives (DSO → BO trace)

| ID | DSO | Maps to | Target | Current state |
|---|---|---|---|---|
| **DSO1** | Detection lead time ≥ 30 minutes between AI-flagged CEM degradation and the threshold-based OSS alarm a NOC operator would otherwise see. | BO1 | ≥ 30 min | Endpoint live (`/granger-causality/lead-time`); wired to dashboard. Lag conversion via `LAG_WINDOW_MINUTES` (currently inherited from monthly grain — operational lead time ships once cycle-grain Granger refresh is in production). |
| **DSO2** | OSS experience anomaly model — VAE recall ≥ 0.70 at precision ≥ 0.35 on hold-out month. | BO1 | R≥0.70, P≥0.35 | **Met**: R=0.700, P=0.377 (operating point), ROC-AUC=0.9821, PR-AUC=0.9974 (`notebooks/models/metrics.json`). |
| **DSO3** | CEM Experience Score regression — R² ≥ 0.95 on hold-out month. | BO1 | R²≥0.95 | **Met**: R²=0.9784 (LightGBM DART, 13 features). |
| **DSO4** | L4 ADN auto-approval rate ≥ 60% on info+prediction actions, **0%** on critical without human approval. Full audit trail. | BO2 | ≥60% / 0% | **Met**: `agent_actions.execution_log` JSONB persists every action with severity-aware classifier (`classifyAction` in l4-agent page). |
| **DSO5** | OSS↔CEM Granger causality — at least 3 statistically significant pairs (p<0.05) covering ≥40% of areas. | BO3 | ≥3 / ≥40% | **Pipeline live**: production engine in `worker/analytics/granger.py`; offline gate in `notebooks/10_granger_feature_selection.py`. Coverage will be reported by `granger_feature_gate.json` after first run. |

---

## 4. KPI Tree

```
BO1 — Catch degradation before complaint
 ├── DSO1 — Lead time minutes
 │     └── Granger best_lag × LAG_WINDOW_MINUTES
 ├── DSO2 — VAE recall / precision
 │     └── notebooks/07_oss_vae_anomaly + ai-service /infer/vae-anomaly
 └── DSO3 — CEM regression R²
       └── notebooks/06_cem_v3_training + ai-service /infer/cem

BO2 — L1 → L4 autonomy lift
 └── DSO4 — Auto-approval rate
       └── classifyAction() + agent_actions.execution_log JSONB

BO3 — OSS+CEM convergence
 └── DSO5 — Granger significance + area coverage
       └── granger_causality_results table + granger_feature_gate.json
```

---

## 5. Methodology Choice

| Aspect | Decision |
|---|---|
| Primary framework | **Hybrid CRISP-DM + MLOps overlay** |
| Reference | CRISP-DM (Chapman 2000) for the 6-phase backbone; Google MLOps Maturity Model (Lvl 1) + Microsoft TDSP for the engineering overlay. |
| Why hybrid | Pure CRISP-DM lacks the containerization / CI-CD / observability vocabulary the jury expects in 2026. Pure TDSP is heavier and less recognized in the Tunisian academic context. The hybrid keeps the academic spine intact while making the existing observability + CI/CD assets first-class evidence. |
| Where each phase lives | See `docs/presentation/v1_outline.md` slide-to-phase mapping. |

---

## 6. Out-of-Scope Statements (defense-time honesty)

1. **HCS migration** — removed. The project is cloud-native by design (microservices, containers, OTel/Prometheus/Grafana/Jaeger), not Huawei-Cloud-bound.
2. **LSTM Churn Trajectory** — deferred. Listed as future work in the deck.
3. **Real NOC alarm baseline** — TT did not share NOC alarm logs, so DSO1 is benchmarked against threshold-based static rules implemented inside the platform, not against a real NOC SLA dashboard.
4. **TT_data confidentiality** — only aggregated metrics are shown. Raw PII (IMSI, TAC, MSISDN) is hashed before any export.
