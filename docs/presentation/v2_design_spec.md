# NeXo — Defense Presentation Design Spec (v2)

> **Tool:** PowerPoint / Google Slides | **Aspect:** 16:9 (33.867cm × 19.05cm)  
> **Time:** 25–30 min | **Slides:** 15 + 2 backup | **Methodology:** Hybrid CRISP-DM + MLOps  
> **Style:** Dark futuristic telecom, glassmorphism, NeXo brand  
> **Owner:** Souhayl Guenichi | **Date:** 2026-05-25

---

## 🎨 Design System

### Color Palette
| Token | Hex | Usage |
|---|---|---|
| `bg-primary` | `#0A0E1A` | Slide background (deep navy black) |
| `bg-card` | `rgba(255,255,255,0.04)` | Glassmorphism card fill |
| `border-glass` | `rgba(255,255,255,0.08)` | Card borders |
| `accent-cyan` | `#00D4FF` | Primary accent — headers, highlights, OSS |
| `accent-magenta` | `#FF006E` | Secondary accent — BSS, alerts, anomalies |
| `accent-gold` | `#FFD700` | Tertiary — KPIs, metrics, stars |
| `text-primary` | `#F0F2F5` | Headlines |
| `text-secondary` | `#8B92A8` | Body, labels |
| `text-muted` | `#4A5068` | Captions, grid lines |
| `success` | `#00E676` | Positive metrics, auto-approved |
| `danger` | `#FF1744` | Critical, anomalies, churn |

### Typography
| Role | Font | Size | Weight | Color |
|---|---|---|---|---|
| Slide title | Inter | 36–44pt | Bold 700 | `text-primary` |
| Phase badge | Inter | 11pt | SemiBold 600 | `accent-cyan` (uppercase, tracking 2px) |
| Body text | Inter | 18–22pt | Regular 400 | `text-secondary` |
| Big number | Space Grotesk | 72–96pt | Bold 700 | `accent-cyan` or `accent-gold` |
| Caption | Inter | 12–14pt | Regular 400 | `text-muted` |
| Narration cue | Inter Italic | 10pt | Light 300 | `text-muted` (Presenter Notes only) |

### Glassmorphism Card Spec
```css
background: rgba(255, 255, 255, 0.04);
backdrop-filter: blur(12px);
border: 1px solid rgba(255, 255, 255, 0.08);
border-radius: 16px;
box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
```
In PowerPoint: Rectangle → Fill: `#FFFFFF` at 4% opacity → Line: `#FFFFFF` at 8% opacity, 0.75pt → Shadow: Outer, black 30% opacity, 8pt blur, offset 0pt.

### Background
- Solid fill: `bg-primary` (`#0A0E1A`)
- Optional subtle texture: 5% opacity dot grid at 40px spacing (`text-muted` color)
- NO gradients on background — keep it clean for screenshot contrast

### CRISP-DM Phase Badge
Top-left corner of every methodology slide. Pill shape:
- Fill: `accent-cyan` at 12% opacity
- Border: `accent-cyan` at 40% opacity, 1pt
- Text: `accent-cyan`, 11pt, uppercase, letter-spacing 2px
- Padding: 4pt vertical, 12pt horizontal
- Radius: 4pt

---

## 📸 Screenshot Inventory

### Notebook Extracts (auto-extracted, located in `docs/presentation/auto_extracted_screenshots/`)

| ID | File | Phase | Slide | Position | Notes |
|---|---|---|---|---|---|
| `N1` | `phase2_eda_inventory_05.png` | Phase 2 | Slide 5 | Left 60% | Data inventory — rows/month, real vs simulated |
| `N2` | `phase2_eda_correlation_08.png` | Phase 2 | Slide 5 | Right 40% | Correlation heatmap (largest, clearest) |
| `N3` | `phase2_eda_missingness_16.png` | Phase 2 | Slide 5 | Bottom strip | Missingness heatmap |
| `N4` | `phase4_cem_feature_importance_00.png` | Phase 4 | Slide 7 | Center | CEM LightGBM feature importance |
| `N5` | `phase4_vae_distribution_00.png` | Phase 4 | Slide 8 | Right 50% | VAE anomaly score distribution |
| `N6` | `phase4_rat_inventory_00.png` | Phase 4 | Slide 9 | Left 50% | RAT underservice model evaluation |

### Dashboard Screenshots You Must Capture

Capture these at **1920×1080**, browser zoom 100%, dark mode if available:

| ID | Page | URL | Slide | What to frame |
|---|---|---|---|---|
| `D1` | Overview | `/overview` | Slide 4 | Full page — KPI cards + pipeline status |
| `D2` | L4 Agent | `/l4-agent` | Slide 12 (live) | Actions tab with pending + auto-approved badges |
| `D3` | Granger Causality | `/granger-causality` | Slide 12 (live) | Lead time histogram + significance table |
| `D4` | Model Evaluation | `/model-evaluation` | Slide 10 | Full metrics page — radar chart + confusion matrices |
| `D5` | CEM Scores | `/cem-scores` | Slide 12 (live) | Score distribution + governorate table |
| `D6` | VAE Anomalies | `/vae-anomalies` | Slide 13 (backup) | Tunisia map with heatmap + top hotspots |
| `D7` | RAT Underservice | `/rat-underservice` | Slide 13 (backup) | Table + stats row |
| `D8` | Pipeline Runs | `/pipeline-runs` | Slide 11 | Run history with 22-step durations |
| `D9` | Tickets | `/tickets` | Slide 13 (backup) | Ticket list showing `TT-YYYY-NNNNN` format |

**Screenshot naming:** Save as `dashboard_<id>_<page>.png`, e.g. `dashboard_D1_overview.png`.

---

## 📑 Slide-by-Slide Blueprint

---

### SLIDE 1 — TITLE / OPENING HOOK
**CRISP-DM:** — (pre-phase)  
**Duration:** 60 sec  
**Layout:** Centered, cinematic, minimal

#### Visual
- Background: `bg-primary` with subtle animated neural grid (static in PPT — use a dark tech background image)
- Center: **NeXo logo** (if available) or stylized "NeXoligence" wordmark in `accent-cyan`
- Below logo: Tagline in `text-secondary`, 22pt:
  > "Cloud-Native AI Operations Agent for OSS+CEM Convergence"
- Bottom third: Three info pills in a row (glassmorphism cards, 200×50pt each):
  - `Souhayl Guenichi`
  - `ESPRIT Engineering School`
  - `Huawei Tunisia — Cloud IT`
- Bottom edge: Date pill `June 2026`

#### Text on Slide (max)
```
NeXoligence
Cloud-Native AI Operations Agent
Souhayl Guenichi | ESPRIT | Huawei Tunisia
```

#### Narration (Presenter Notes)
> "Good morning, jury. I'm Souhayl Guenichi, an ESPRIT engineering student who spent the last six months at Huawei Tunisia building something that shouldn't exist yet — an autonomous AI operations agent that closes the gap between network engineers and customer experience teams. This is NeXoligence."

---

### SLIDE 2 — THE PAIN HOOK
**CRISP-DM:** Phase 1 — Business Understanding  
**Duration:** 90 sec  
**Layout:** Split-screen, high contrast

#### Visual
- Left half (50%): Dark zone labeled **"OSS WORLD"**
  - Icon: Cell tower + green status dots
  - Big text: `NORMAL` in `success`
  - Sub: "Network KPIs are green. Alarms are silent."
- Right half (50%): Dark zone labeled **"BSS WORLD"**
  - Icon: Subscriber avatar + red churn alert
  - Big text: `CHURNING` in `danger`
  - Sub: "Customers are complaining. Revenue is leaking."
- Center gap: A **broken bridge icon** or gap symbol in `text-muted`
- Bottom center (full width): Glassmorphism banner:
  > "Network anomalies are invisible to OSS until a customer complaint reaches Care."

#### Text on Slide
```
OSS WORLD              [GAP]              BSS WORLD
NORMAL                                    CHURNING
"All KPIs green"                          "Customers leaving"
```

#### Narration
> "In every telecom operator, two planets orbit each other but never touch. The network team sees green KPIs. The care team sees angry customers. The problem? By the time OSS detects an anomaly, the subscriber has already churned. NeXoligence was built to bridge that gap."

---

### SLIDE 3 — STAKEHOLDER OBJECTIVES (BO + DSO + KPI TREE)
**CRISP-DM:** Phase 1 — Business Understanding  
**Duration:** 90 sec  
**Layout:** Three-column hierarchy

#### Visual
- Phase badge top-left: `PHASE 1 — BUSINESS UNDERSTANDING`
- Three glassmorphism columns, equal width, gap 16pt:

**Column 1 — Business Objectives (BO)**
- Header: `BUSINESS OBJECTIVES` in `accent-cyan`
- BO1: "Reduce CEM-to-action latency"
- BO2: "Automate NOC triage"
- BO3: "Enable predictive capacity planning"

**Column 2 — Data Science Objectives (DSO)**
- Header: `DATA SCIENCE OBJECTIVES` in `accent-magenta`
- DSO1: CEM score prediction (R² > 0.99)
- DSO2: Anomaly detection (AUC > 0.90)
- DSO3: RAT underservice classification
- DSO4: OSS+BSS correlation engine
- DSO5: Granger-validated lead time

**Column 3 — KPIs**
- Header: `TARGET KPIs` in `accent-gold`
- Three metric cards:
  - `R² ≥ 0.99` ✅
  - `AUC ≥ 0.93` ✅
  - `Lead Time ≥ 15 min` ✅

- Bottom banner: "All 5 DSOs met by v3 release."

#### Narration
> "The project was anchored in real business objectives provided by Tunisie Telecom and Huawei. Every data science objective maps directly to a business outcome. And every target KPI you see here — the 99.9% R-squared, the 93% AUC, the 15-minute lead time — was achieved and validated on real data."

---

### SLIDE 4 — METHODOLOGY (HYBRID CRISP-DM + MLOPS)
**CRISP-DM:** Cross-cutting methodology  
**Duration:** 60 sec  
**Layout:** Horizontal process flow

#### Visual
- Top: Phase badge `METHODOLOGY`
- Center: Six hexagons in a horizontal chain, connected by glowing lines:
  1. `Business Understanding` — cyan glow
  2. `Data Understanding` — cyan glow
  3. `Data Preparation` — cyan glow
  4. `Modeling` — magenta glow
  5. `Evaluation` — magenta glow
  6. `Deployment` — gold glow
- Below hexagons: Two-layer label:
  - Top layer: "CRISP-DM (Chapman 2000) — Academic spine"
  - Bottom layer: "MLOps Overlay — CI/CD, observability, hot-reload, closed-loop actuation"
- Right side: Small glass card with citations:
  - Google MLOps Maturity Level 1
  - Microsoft TDSP
  - Huawei ADN L4 Framework

#### Narration
> "The methodology is hybrid. CRISP-DM provides the six-phase academic spine. But this isn't a classroom project — it's industrial. So I overlaid MLOps: continuous integration, automated retraining, observability stacks, and a closed-loop actuation layer. The result is a platform that behaves like a product, not a prototype."

---

### SLIDE 5 — PHASE 2: DATA UNDERSTANDING
**CRISP-DM:** Phase 2 — Data Understanding  
**Duration:** 120 sec  
**Layout:** Screenshot collage with annotations

#### Visual
- Phase badge: `PHASE 2 — DATA UNDERSTANDING`
- Left zone (55%): **Screenshot `N1`** (`phase2_eda_inventory_05.png`)
  - Caption below: "968K real BSS + 18.8M real OSS records. 6 months span."
- Right top (45%): **Screenshot `N2`** (`phase2_eda_correlation_08.png`)
  - Caption: "Pearson + Spearman correlation matrices — early convergence signal."
- Right bottom (45%): **Screenshot `N3`** (`phase2_eda_missingness_16.png`)
  - Caption: "Missingness audit — <2% NaN, mean-imputation validated."
- Bottom strip: Three mini stat pills:
  - `2.47M` Total records processed
  - `26` Features per subscriber
  - `<2%` Missing rate

#### Narration
> "Phase two was a full data autopsy. Nearly a million real Tunisie Telecom subscribers. 18.8 million cell-level KPIs. I ran correlation matrices, missingness heatmaps, outlier detection with IsolationForest, and generator validation overlays. The data was cleaner than expected — under two percent missing — and the correlations between OSS and BSS variables were strong enough to justify the convergence hypothesis."

---

### SLIDE 6 — PHASE 3: DATA PREPARATION
**CRISP-DM:** Phase 3 — Data Preparation  
**Duration:** 90 sec  **Layout:** Two-panel horizontal

#### Visual
- Phase badge: `PHASE 3 — DATA PREPARATION`
- Left panel (50%): **Data Augmentation Module**
  - Icon: Stack of layers (raw → processed → curated)
  - Label: `Bootstrap Simulation Engine`
  - Three bullet-cards (max 3 words each):
    - "Stratified bootstrap"
    - "Log-normal drift"
    - "Identity replacement"
  - Stat: `1.5M` simulated records generated
- Right panel (50%): **Granger Feature Gate**
  - Icon: Funnel filter
  - Label: `Granger Causality Gate`
  - Text:
    - "Offline F-test → feature selection"
    - "Only Granger-validated features enter training"
    - "Lag window configurable per area"
  - Output file badge: `granger_feature_gate.json`
- Center connector arrow: `AUGMENTED DATA → FILTERED FEATURES`

#### Narration
> "Phase three had two engines. First, a bootstrap simulation module that generated 1.5 million realistic subscriber records from real reservoirs — preserving distributions while injecting temporal drift. Second, the Granger gate: an offline causality filter that only lets features into training if they pass an F-test for predictive causality on OSS-to-BSS lag. This is what separates correlation from causation."

---

### SLIDE 7 — PHASE 4: MODELING — EXPERIENCESPIRIT (CEM)
**CRISP-DM:** Phase 4 — Modeling  
**Duration:** 90 sec  
**Layout:** Model card + screenshot

#### Visual
- Phase badge: `PHASE 4 — MODELING`
- Left (40%): **Model Card** (glassmorphism)
  - Spirit icon/badge: `ExperienceSpirit`
  - Algorithm: `LightGBM DART`
  - Hyperparams: `256 leaves | depth=12 | 5-fold CV`
  - Training: `2.47M subscribers | 5 months`
  - Big metric: `R² = 0.9995` in `accent-cyan`
  - Secondary: `MAE = 0.0013`
- Right (60%): **Screenshot `N4`** (`phase4_cem_feature_importance_00.png`)
  - Caption: "Top SHAP features — DOU, traffic, RAT gap dominate."
- Bottom: Small label: `v3.0 deployed | Hot-reloadable | GPU-trained`

#### Narration
> "ExperienceSpirit is the CEM scoring engine. LightGBM with DART boosting, 256 leaves, depth twelve. Trained on 2.47 million subscribers. The R-squared is 0.9995 — meaning the model explains 99.95% of variance in customer experience. The feature importance confirms what domain experts expect: data usage, traffic volume, and RAT gap are the dominant predictors."

---

### SLIDE 8 — PHASE 4: MODELING — NETWORKSPIRIT (VAE)
**CRISP-DM:** Phase 4 — Modeling  
**Duration:** 75 sec  
**Layout:** Model card + screenshot

#### Visual
- Left (40%): **Model Card**
  - Spirit badge: `NetworkSpirit`
  - Algorithm: `PyTorch VAE`
  - Architecture: `9 → 32 → 16 → Latent(8)`
  - Training: `1M OSS records | normal-only`
  - Big metric: `ROC-AUC = 0.931` in `accent-magenta`
  - Secondary: `Recall = 0.702`
- Right (60%): **Screenshot `N5`** (`phase4_vae_distribution_00.png`)
  - Caption: "Latent space reconstruction error — anomalies are outliers."
- Bottom label: `Unsupervised | Real-time inference | Anomaly score 0-1`

#### Narration
> "NetworkSpirit is the anomaly detector. It's a variational autoencoder trained only on normal network behavior. When reconstruction error spikes, an anomaly is flagged. The ROC-AUC of 93.1% means it correctly ranks anomalies against normal records with outstanding precision. And because it's unsupervised, it detects anomalies no human has ever labeled before."

---

### SLIDE 9 — PHASE 4: MODELING — UNDERSERVICESPIRIT (RAT) + ADN L4
**CRISP-DM:** Phase 4 — Modeling  
**Duration:** 90 sec  
**Layout:** Two-part vertical

#### Visual
**Top half:**
- Left (40%): **Model Card**
  - Spirit badge: `UnderserviceSpirit`
  - Algorithm: `XGBoost GPU`
  - Hyperparams: `500 trees | depth=8 | GPU-accelerated`
  - Training: `2.47M subscribers`
  - Big metric: `ROC-AUC = 0.955` in `accent-gold`
  - Secondary: `F1 = 0.560`
- Right (60%): **Screenshot `N6`** (`phase4_rat_inventory_00.png`)
  - Caption: "RAT gap classification — identifies 4G/5G underservice."

**Bottom half:**
- Full-width glass card: `ADN L4 AUTONOMOUS AGENT`
- Four spirit icons in a row: ExperienceSpirit | NetworkSpirit | UnderserviceSpirit | ConvergenceSpirit
- Label: "Spirits run inference. Mates run chat + synthesis. ActionSpirit closes the loop."
- Right: `L4` badge (large, pulsing glow effect if animated)

#### Narration
> "UnderserviceSpirit uses XGBoost on GPU to identify subscribers stuck on legacy RATs who should be migrated to 4G or 5G. 95.5% ROC-AUC. All three spirits feed into the L4 Autonomous Agent — Huawei's ADN Level 4 paradigm. The agent auto-approves safe actions, escalates critical ones, and maintains a full audit trail."

---

### SLIDE 10 — PHASE 5: EVALUATION
**CRISP-DM:** Phase 5 — Evaluation  
**Duration:** 90 sec  
**Layout:** Metrics dashboard + screenshot

#### Visual
- Phase badge: `PHASE 5 — EVALUATION`
- Top row: Three big-number cards:
  - `R² 0.9995` / CEM LightGBM
  - `AUC 0.931` / VAE Anomaly
  - `AUC 0.955` / RAT XGBoost
- Middle: **Screenshot `D4`** (Model Evaluation page)
  - Frame it with a glassmorphism border
  - Caption: "Live metrics from /model-evaluation — custom SVG visualizations, zero chart libraries."
- Bottom row: Two insight cards:
  - Left: `Granger Lead Time: 15+ min` — "OSS anomaly predicts CEM drop 15 minutes before complaint."
  - Right: `Convergence: 5 pairs validated` — "Pearson + Spearman + Granger F-test on OSS↔BSS pairs."

#### Narration
> "Evaluation isn't a single number. For regression, R-squared and MAE. For anomaly detection, ROC-AUC and recall. For classification, F1 and AUC. But the real validation is convergence: Granger causality proves that network events cause experience degradation with a measurable 15-minute lead time. That's not correlation. That's causation. And that's the competitive advantage."

---

### SLIDE 11 — PHASE 6: DEPLOYMENT
**CRISP-DM:** Phase 6 — Deployment  
**Duration:** 90 sec  **Layout:** Architecture diagram + observability stack

#### Visual
- Phase badge: `PHASE 6 — DEPLOYMENT`
- Center: **3-layer isometric stack** (use a clean diagram, not a screenshot):
  - **Bottom:** Data Lake — MinIO (Raw → Processed → Curated)
  - **Middle:** Microservices — 15 containers (api-gateway, ai-service, auth-service, pipeline-worker, agent-service...)
  - **Top:** Frontend — Next.js dashboard + L4 Agent
- Right side: **Observability Stack** (vertical list with icons):
  - Netdata → real-time containers
  - Prometheus → metrics TSDB
  - Grafana → dashboards
  - Jaeger → distributed traces
  - OTel Collector → unified telemetry
- Bottom: **CI/CD Badge** — GitHub Actions 6-stage pipeline:
  `LINT → TEST → BUILD → INTEGRATE → SECURITY → DEPLOY`
- Small text: "Cloud-native by design. HCS-ready: MinIO→OBS, Postgres→RDS, Docker→ECS."

#### Narration
> "Deployment is where academic projects die and industrial projects survive. NeXoligence runs 15 microservices in Docker. The pipeline cycles every two minutes. Observability covers metrics, traces, and logs. CI/CD has six stages including security scanning. And the entire architecture is mapped to Huawei Cloud Stack — local now, cloud next."

---

### SLIDE 12 — LIVE DEMO STORYBOARD
**CRISP-DM:** Cross-cutting (Demo)  
**Duration:** 180 sec (3 min live demo)  
**Layout:** 4-panel storyboard

#### Visual
- Title: `LIVE DEMO — 4 STATIONS`
- Four equal glassmorphism panels in a 2×2 grid:

**Panel 1:** `1. Overview`
- Thumbnail: **Screenshot `D1`** (Overview page)
- Label: "Platform heartbeat — cycle count, anomalies, L4 status."

**Panel 2:** `2. L4 Agent`
- Thumbnail: **Screenshot `D2`** (L4 Agent actions tab)
- Label: "Auto-approved vs pending. Real playbook execution."

**Panel 3:** `3. Granger Causality`
- Thumbnail: **Screenshot `D3`** (Granger page)
- Label: "Lead time histogram + statistical significance table."

**Panel 4:** `4. Model Evaluation`
- Thumbnail: **Screenshot `D4`** (Model Evaluation)
- Label: "Real metrics, confusion matrices, radar comparison."

- Bottom center: `Demo URL: http://localhost:3001` + login credentials pill
- Small warning icon: "Backup slides follow in case of network failure."

#### Narration (Presenter Notes — read before switching to laptop)
> "Now I'll show you the platform live. Four stations. First, the overview — the platform's heartbeat. Second, the L4 agent where actions are generated, auto-approved, or escalated. Third, Granger causality with real lead-time histograms. And fourth, the model evaluation page with metrics trained on real data. If anything fails, backup screenshots are on the next slides."

---

### SLIDE 13 — DEMO BACKUP A (DASHBOARD SCREENS)
**CRISP-DM:** Backup (static)  
**Duration:** 60 sec (only if live fails)  
**Layout:** Screenshot gallery

#### Visual
- Title: `DEMO BACKUP — PLATFORM SCREENS`
- Top row: Two screenshots side by side:
  - Left: **Screenshot `D5`** (CEM Scores)
  - Right: **Screenshot `D6`** (VAE Anomalies with Tunisia map)
- Bottom row: Two screenshots side by side:
  - Left: **Screenshot `D7`** (RAT Underservice)
  - Right: **Screenshot `D9`** (Tickets with auto-sequencing)
- Each screenshot framed in glassmorphism border with page name label below.

#### Narration (if used)
> "If the live demo had failed, these are the real screens. CEM scores by governorate. The Tunisia anomaly heatmap. RAT underservice browser. And auto-sequenced NOC tickets. Every pixel is real data."

---

### SLIDE 14 — LIMITATIONS & FUTURE WORK
**CRISP-DM:** — (post-phase)  
**Duration:** 60 sec  
**Layout:** Two-column honesty slide

#### Visual
- Title: `LIMITATIONS & FUTURE WORK`
- Left column: `CURRENT LIMITATIONS` (text-muted headers, danger accents)
  - "LSTM Churn deferred — needs rolling window history"
  - "Real NOC alarm baseline not integrated"
  - "Granger refresh is monthly, not cycle-grain"
- Right column: `FUTURE WORK` (success accents)
  - "LSTM Churn Trajectory — 4th model"
  - "Postgres LISTEN/NOTIFY event-driven pipeline"
  - "TimescaleDB hypertables for OSS time-series"
  - "Redis pipeline state + multi-agent collaboration"
- Bottom: Timeline bar from `Now` → `v4.0` → `HCS Production`

#### Narration
> "No project is perfect. The LSTM churn model was deferred because it needs accumulated window history. The NOC alarm baseline wasn't available. And Granger refresh is monthly. But the roadmap is clear: the fourth model, event-driven pipelines, TimescaleDB, and multi-agent collaboration are all scoped for version four."

---

### SLIDE 15 — CLOSING / THANK YOU
**CRISP-DM:** — (post-phase)  
**Duration:** 30 sec  
**Layout:** Cinematic, minimal, memorable

#### Visual
- Center: Large `NeXoligence` wordmark in `accent-cyan`
- Below: Tagline in `text-secondary`
  > "From data to decision. Autonomously."
- Bottom row: Three contact pills:
  - `GitHub: ghcr.io/souhayl1g/...`
  - `Email: souhayl.guenichi@...`
  - `Demo: localhost:3001`
- Center bottom: `Questions?` in 48pt, `accent-gold`

#### Narration
> "NeXoligence proves that autonomous AI operations aren't science fiction — they're engineering. A six-month internship, a full-stack platform, three production models, and a closed-loop actuation layer. Thank you. I'm ready for your questions."

---

## 🎬 Demo Execution Guide

### Pre-Defense Checklist
```
[ ] Stack running: docker compose ps (all healthy)
[ ] Dashboard reachable: http://localhost:3001
[ ] Login works with test credentials
[ ] Pipeline has run at least once today (fresh data)
[ ] L4 Agent has pending or auto-approved actions visible
[ ] Granger page shows lead-time histogram (not empty)
[ ] Screenshots D1–D9 captured and copied to backup USB
[ ] Slides 12 and 13 tested — hyperlink to demo or seamless Esc
```

### Live Demo Flow (3 minutes)
| Time | Action | What to Say |
|---|---|---|
| 0:00 | Switch to browser, open `/overview` | "This is the platform heartbeat." |
| 0:30 | Navigate to `/l4-agent`, Actions tab | "The L4 agent generates actions from live data." |
| 0:60 | Click an auto-approved action, show log | "Safe actions are auto-approved and audited." |
| 1:15 | Navigate to `/granger-causality` | "Granger causality gives us predictive lead time." |
| 1:45 | Navigate to `/model-evaluation` | "Every metric is real, trained on TT data." |
| 2:15 | Briefly show `/vae-anomalies` map | "And this is where anomalies happen — geographically." |
| 2:45 | Back to slides | "Back to the deck." |

---

## 📁 File Deliverables

After this spec is approved, the following files will be produced:

| File | Purpose |
|---|---|
| `v2_design_spec.md` | This document — master blueprint |
| `slide_master.pptx` | PowerPoint file with master slides, colors, fonts preset |
| `auto_extracted_screenshots/` | 24 notebook PNGs + `_inventory.json` |
| `dashboard_screenshots/` | Your 9 captures, renamed and framed |
| `narration_script.docx` | Presenter notes only, printable |

---

## ✅ Approval Sign-Off

| Checkpoint | Status |
|---|---|
| Slide count (15) approved | ⬜ |
| CRISP-DM phase mapping approved | ⬜ |
| Screenshot inventory complete | ✅ Auto-extracted |
| Dashboard screenshot list approved | ⬜ Waiting for your capture |
| Color palette & typography approved | ⬜ |
| Narration tone approved | ⬜ |

**Next step:** You capture dashboard screenshots D1–D9, upload them here. I then label each one, build the final slide positioning, and if you want, generate a `.pptx` master template.
