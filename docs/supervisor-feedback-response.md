# Supervisor Feedback — Honest Assessment & Clarification

> Meeting: April 15, 2026 | Feedback from academic technical supervisor
> Purpose: Address every question directly, no hand-waving

---

## The Questions He Asked (and He's Right)

1. What is the **final output** of the project?
2. What is the **input** of the ADN L4 agent and what does it **actually do**?
3. Where is the **autonomy**? Where is the **driving**?
4. Is the agent a **recommendation system**? If yes, call it that.
5. Where will models be **trained**? Local or hosted? Is it heavy?
6. Many features but the **output is blur**.

Let me answer each one with total honesty.

---

## Question 1: "What Is the Final Output?"

**The honest problem:** I've been building technically impressive infrastructure (10 microservices, 5 ML/DL models, rolling window engine, 15 dashboard pages) but I haven't crisply defined: **what does the operator GET from this platform that they don't have today?**

**The crisp answer — 4 concrete outputs:**

### Output 1: CEM Subscriber Segmentation Map
```
INPUT:  500K raw subscriber records (26 features)
OUTPUT: Every subscriber classified into an experience segment:

  ┌──────────────────────────────────────────────────────┐
  │  Segment              │ Count   │ Action              │
  │───────────────────────│─────────│─────────────────────│
  │  Well-served          │ 245K    │ Retain (no action)  │
  │  Underserved (SIM)    │  87K    │ SIM upgrade campaign│
  │  Underserved (coverage│  42K    │ Network investment   │
  │  Degrading experience │  28K    │ Proactive support   │
  │  Churn risk (Silent)  │  58K    │ Win-back campaign   │
  │  Anomalous profile    │  40K    │ Investigation       │
  └──────────────────────────────────────────────────────┘
```

**Why this matters:** Today, Tunisie Telecom has 500K rows in a flat file. Nobody knows which subscribers are underserved, which are about to churn, or which have anomalous profiles. My platform turns a flat file into an actionable segmentation. Each segment has a CVM (Customer Value Management) action attached.

### Output 2: O+B Convergence Report
```
INPUT:  BSS subscriber aggregates (by area/delegation/RAT) +
        OSS cell KPIs (by site/RAT) — paired time series
OUTPUT: For each region:
  - Correlation strength between network quality and subscriber experience
  - Causal direction (does network degradation CAUSE experience drops?)
  - Affected subscriber count
  - Specific KPIs driving the correlation

Example output:
  "Sfax Medina, 4G: Pearson=0.87, Granger p=0.003 (OSS→BSS, lag=2)
   Cell throughput drop causes CEM score degradation for ~4,200 subscribers.
   Top driver: s1_mme_sr collapse when throughput < 15 Mbps."
```

**Why this matters:** Today, the network team sees cell KPIs and the business team sees subscriber complaints. Nobody connects them. This output tells them: "Fix THIS cell, it's hurting THESE subscribers."

### Output 3: Real-Time Anomaly & Churn Dashboard
```
INPUT:  Rolling window engine feeding models every 2 minutes
OUTPUT: Live dashboard showing:
  - Experience anomalies detected this cycle (Autoencoder)
  - Subscribers trending toward churn (LSTM trajectory)
  - Current CEM scores by region/delegation
  - Underservice hotspots (geographic heatmap)
```

### Output 4: Agent Action Log (Decision Support)
```
INPUT:  All model outputs + thresholds + business rules
OUTPUT: Prioritized list of recommended actions with:
  - What to do (specific playbook)
  - Why (model output + feature explanation)
  - Who is affected (subscriber count, region)
  - Confidence level
  - Urgency (auto-executed vs needs approval)
```

---

## Question 2: "What Is the L4 Agent's Input and What Does It Actually Do?"

**Honest assessment of the current state:**

Right now, the L4 agent does this:
```
1. Reads platform data (SLA scores, anomalies, correlations) from API
2. Applies IF/THEN rules to generate actions (generateActions function)
3. Classifies actions as "needs approval" or "auto-approved"
4. When approved, executes a playbook (SQL query + analysis)
5. Stores result in PostgreSQL
```

**What the playbooks ACTUALLY do today:**
- `pb-anomaly-triage`: Queries recent anomalies, classifies by severity, cross-references correlations → produces a **report** (JSON)
- `pb-sla-breach`: Reads SLA score, checks which KPIs breach thresholds → produces a **report**
- `pb-capacity-scale`: Computes capacity headroom from KPI history → produces a **report**
- `pb-model-retrain`: Calls ai-service /models/reload → actually **does** something (reloads models)
- `pb-revenue-protect`: Queries flagged subscribers → produces a **report**

**The honest truth:** 4 out of 5 playbooks produce reports, not actions. Only model-retrain does something. The agent is currently a **decision support system with automated reporting**, not an autonomous operator.

---

## Question 3: "Where Is the Autonomy? Where Is the Driving?"

**This is the hardest question and he's right to ask it.**

### What ADN L4 Actually Means in Huawei's Framework

L4 = "The system handles most situations autonomously. Human oversight is needed only for complex/novel scenarios."

In a real ADN L4 telecom system, the autonomous actions would be:
```
NETWORK LEVEL (OSS):
  - Auto-scale cell capacity (add carriers, adjust power)
  - Auto-reroute traffic from degraded cells
  - Auto-trigger cell restart on persistent alarms
  - Auto-adjust handover parameters

SUBSCRIBER LEVEL (BSS/CVM):
  - Auto-trigger SIM upgrade SMS to underserved subscribers
  - Auto-apply QoS boost for degrading subscribers
  - Auto-assign priority handling for high-value churning subscribers
  - Auto-generate trouble tickets for anomalous profiles
```

**What my platform can realistically do (as an intelligence layer, not a network controller):**

I don't have direct access to the RAN (Radio Access Network), the HLR/HSS, or the CRM system. I can't actually reconfigure cells or send SMS to subscribers. My platform sits ABOVE those systems as an intelligence layer.

### Redefining What L4 Means for This Project

The autonomy isn't in the NETWORK ACTION — it's in the INTELLIGENCE LOOP:

```
Level 0-2: Human reads dashboard, decides what to investigate, runs queries manually
Level 3:   System alerts human to issues, human decides what to do
Level 4:   System detects → diagnoses → recommends specific action → auto-executes
           safe actions (reporting, model updates, ticket creation) →
           presents risky actions with full explanation for human approval
```

**The concrete L4 behaviors:**

| What It Does Autonomously (no human) | What It Does With Approval |
|--------------------------------------|---------------------------|
| Detects anomalies every 2 min (Autoencoder) | Triggers model retraining when drift detected |
| Scores every subscriber's experience (GBR) | Escalates critical O+B correlation findings |
| Classifies underservice root cause (XGBoost) | Generates CVM action lists (SIM upgrade targets) |
| Predicts churn trajectory (LSTM) | Recommends network investment priorities |
| Computes O+B correlations (Granger) | Flags anomalous subscriber clusters for investigation |
| Generates prioritized action queue | - |
| Auto-approves informational actions | - |

**The L4 agent's real value:** It's not replacing a network engineer clicking buttons. It's replacing the ANALYSIS WORKFLOW that today takes a team of analysts days or weeks:

```
TODAY (without platform):
  1. Export BSS data to Excel (manual, hours)
  2. Analyst looks at subscriber metrics (days)
  3. Someone notices churn trend (maybe, weeks later)
  4. Someone else correlates with network issues (cross-team meeting)
  5. Action plan created (another week)
  Total: weeks to months

WITH PLATFORM (L4 intelligence):
  1. Pipeline ingests data automatically (2-min cycles)
  2. Models detect anomalies, score experience, predict churn (seconds)
  3. Correlation engine links to network causes (seconds)
  4. Agent generates prioritized action list with explanations (immediate)
  5. Human approves critical actions, safe actions auto-execute
  Total: minutes
```

**The autonomy is in the intelligence, not the network control.** The "driving" is: the system drives the analysis, drives the diagnosis, drives the prioritization, and drives safe reporting actions — all without human intervention.

---

## Question 4: "Is It a Recommendation System? Call It What It Is"

**Yes and no. Let me be precise:**

It's a **closed-loop decision support system with selective autonomy**. That's not just semantics — here's the difference:

| System Type | What It Does | My Platform |
|-------------|-------------|-------------|
| Dashboard | Shows data, human interprets | No — my platform INTERPRETS the data (models) |
| Alert system | Fires when threshold crossed | Partially — but also predicts BEFORE threshold |
| Recommendation system | Suggests actions, human does all | Partially — but it also auto-executes safe ones |
| ADN L4 agent | Autonomous with human oversight | Yes — detects, diagnoses, acts, with approval for risky |

The distinguishing factor from a pure recommendation system:
1. It **auto-executes** safe actions (reporting, monitoring, model management)
2. It **generates the analysis**, not just the alert (playbook execution produces a complete diagnostic report, not just "something is wrong")
3. It **maintains state** across cycles (persisted actions, window history, model versions)
4. It **learns** (models retrained on real data, drift detection triggers retraining)

**For the presentation/report, I would position it as:**

> "An ADN L4 intelligence agent that autonomously detects, diagnoses, and recommends actions for subscriber experience management, with selective human oversight for critical interventions."

---

## Question 5: "Where Will Models Be Trained? Is It Heavy?"

**Direct answer: Training is lightweight. All local. No GPU needed.**

| Model | Training Time (500K rows) | Hardware | Where |
|-------|--------------------------|----------|-------|
| CEM Score (GBR, 200 trees) | ~30 seconds | CPU only | Jupyter notebook → joblib |
| Experience Anomaly (Autoencoder) | ~3-5 minutes (50 epochs) | CPU only (PyTorch CPU) | Jupyter notebook → TorchScript |
| Churn LSTM | ~5-10 minutes (30 epochs) | CPU only | Jupyter notebook → TorchScript |
| RAT Underservice (XGBoost) | ~15 seconds | CPU only | Jupyter notebook → joblib |
| O+B Correlation | ~10 seconds | CPU only (scipy) | pipeline-worker inline |

**Total training time: under 20 minutes for all 5 models on a laptop.**

**Why it's not heavy:**
- 500K rows × 42 features is a medium dataset. It fits in memory (~200 MB).
- The DL models are SMALL: Autoencoder is 5 layers (~50K parameters). LSTM is 4 layers (~30K parameters). These are not GPT-scale models.
- GBR and XGBoost are CPU-native — they don't benefit from GPU.
- PyTorch CPU-only is sufficient. No CUDA needed.

**Training workflow:**
```
1. Train in Jupyter notebooks (on laptop or any machine with Python)
2. Evaluate (metrics, cross-validation)
3. Export model files (.joblib, .pt)
4. Place in ai-service/models/ directory (Docker volume)
5. ai-service loads on startup or via /models/reload endpoint

No cloud training needed. No GPU cluster. No MLflow server.
```

**For HCS deployment later:** Training would happen on a ModelArts notebook instance (Huawei's Jupyter equivalent). Same code, same data, same results. The models are portable.

---

## Question 6: "Many Features But the Output Is Blur"

**He's absolutely right. Here's why it happened and how to fix it.**

### Why the output became blur

I focused on building the TECHNICAL DEPTH (26 features → 16 engineered → 5 models → rolling window → microservices) without stepping back to define: **what does the operator SEE on their screen that makes their job easier?**

I have 15+ dashboard pages but the STORY they tell isn't clear. A network operations manager opening the platform should immediately understand:
1. How many subscribers have good/bad experience right now?
2. What are the top 3 problems and what should I do about them?
3. Is the situation getting better or worse?

### The Fix: Define 3 Clear Deliverables

**Deliverable 1: CEM Scorecard (the "at a glance" output)**
```
┌──────────────────────────────────────────────────────┐
│  TUNISIE TELECOM — CEM INTELLIGENCE SCORECARD        │
│  March 2026 | 500,000 subscribers analyzed           │
│                                                      │
│  Overall CEM Score: 0.72 / 1.00    [▓▓▓▓▓▓▓░░░]    │
│                                                      │
│  ✓ Well-served:     245,000 (49%)                    │
│  ⚠ Underserved:     129,000 (26%)                    │
│  ✗ At-risk/Silent:   86,000 (17%)                    │
│  ? Anomalous:        40,000 (8%)                     │
│                                                      │
│  TOP 3 ACTIONS:                                      │
│  1. SIM upgrade campaign → 87K subscribers            │
│     (USIM=0 blocking 4G access, est. 35% uplift)    │
│  2. Sfax Medina 4G investigation → 4,200 affected    │
│     (O+B: cell degradation causing attach failures)  │
│  3. Churn prevention for 12,000 degrading subs       │
│     (LSTM: trajectory toward Silent within 3 months) │
└──────────────────────────────────────────────────────┘
```

**Deliverable 2: O+B Convergence Report (the unique value)**
```
"Here are the areas where network problems are hurting subscribers,
 ranked by impact, with specific cells to fix."
```

**Deliverable 3: Operational Agent (the continuous value)**
```
"Every 2 minutes, the platform re-evaluates all subscribers,
 detects new anomalies, updates churn predictions,
 and generates a prioritized action queue."
```

### What Changed After This Feedback

The project output is now:

> **A CEM intelligence platform that takes raw subscriber and network data, produces a subscriber experience scorecard with actionable segments, identifies where network issues cause subscriber impact (O+B convergence), and continuously monitors for anomalies and churn through an autonomous agent — all running as cloud-native microservices deployable on Huawei Cloud Stack.**

One sentence. Clear input, clear output, clear value.

---

## Updated Architecture With Clear Input→Output Flow

```
INPUT                         PROCESSING                        OUTPUT
─────                         ──────────                        ──────

BSS: 500K subscribers ───→ Feature Engineering ───→ CEM Scorecard
  26 features                16 derived features      (subscriber segmentation
  (device, usage,                    │                  with action per segment)
   network quality,                  │
   geography)                        ├──→ GBR CEM Score
                                     ├──→ Autoencoder Anomaly
                                     ├──→ XGBoost Underservice
                                     │
                                     ├──→ Rolling Window ──→ LSTM Churn Prediction
                                     │
OSS: Cell KPIs ─────────→           ├──→ O+B Correlation ──→ Convergence Report
  (waiting for data)                 │      Engine              (root cause: network
                                     │                           → subscriber impact)
                                     │
                                     └──→ L4 Agent ──→ Action Queue
                                            │            (prioritized, with
                                            │             explanations)
                                            │
                                            ├──→ Auto-execute safe actions
                                            └──→ Present risky for approval
```

---

## Action Items After This Meeting

1. **Sharpen the output narrative** — every dashboard page should connect to one of the 3 deliverables
2. **Be honest about L4 scope** — it's intelligence-layer L4, not network-control L4. Say that clearly.
3. **Training is lightweight** — emphasize this. It's a feature, not a weakness. It means the platform is deployable on standard infrastructure.
4. **CEM Scorecard is the hero output** — if the supervisor (or anyone) asks "what does this produce?", the scorecard is the answer.
