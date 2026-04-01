# Dokie AI Prompt — Supervisor Meeting Presentation (11 Slides)

Copy-paste the following prompt into Dokie AI to generate a **supervisor meeting** presentation. This is an overview of the project idea and outputs — not a final defense. Keep it high-level, visual, diagram-heavy, no code or ports.

---

## PROMPT START

Create a **professional presentation** (16:9 aspect ratio, **exactly 11 slides**) for a **supervisor progress meeting** about a PFE (End-of-Studies) project at ESPRIT university, done at **Huawei Tunisia — Cloud IT / Sales-Solution**.

This is NOT the final defense — it is a **progress meeting** to present our idea, approach, and outputs so far. Keep it **high-level and visual** — no code, no port numbers, no implementation details. Focus on the **what and why**, not the how.

### Project Title
**Cloud-Native AI Operations Agent for CEM–CVM Intelligence**
*An Autonomous Agent That Detects, Decides, and Acts*

### Student
Souhayl Guenichi | ESPRIT | Huawei Tunisia | Academic Year 2025–2026

### Design Style
- Modern, clean, dark-background with accent colors
- Primary: **#CF0A2C** (Huawei red), Secondary: **#8E44AD** (AI violet), Tertiary: **#2E86AB** (OSS blue), **#2ECC71** (BSS green), Accent: **#E74C3C** (Action red)
- Minimal text, visual-heavy, professional icons (no emojis)
- Use diagrams on every possible slide
- Professional font (Inter, Poppings, or similar)

### Slide Structure (11 Slides)

**Slide 1 — Title Slide**
- Project title: "Cloud-Native AI Operations Agent for CEM–CVM Intelligence"
- Subtitle: "An Autonomous Agent That Detects, Decides, and Acts"
- Student: Souhayl Guenichi | ESPRIT x Huawei Tunisia | March 2026
- Supervisor meeting — Progress Overview

**Slide 2 — The Problem**
- Telecom operators have two data worlds that never talk to each other:
  - OSS (Network): throughput, latency, packet loss, signal quality
  - BSS (Business): revenue, churn, data usage, ARPU
- When the network degrades, the business feels it days later — nobody connects the dots
- No existing system bridges this gap AND takes autonomous action
- Visual: Two silos with a red "GAP" between them

**Slide 3 — Our Solution: The AI Operations Agent**
- Central diagram: CEM (Huawei SmartCare) --> AI Operations Agent --> CVM (Customer Value Management)
- The agent sits between experience management and value management
- Three core capabilities: DETECT (anomalies + SLA risk) | DECIDE (correlate network + business) | ACT (generate recommendations)
- Positioned at ADN Level 4 (Highly Autonomous) — AI decides and acts, humans handle edge cases only
- Visual: Use Diagram #1 (CEM-Agent-CVM positioning)

**Slide 4 — How It Works: 5-Phase Pipeline**
- High-level visual pipeline (no implementation details):
  - Phase 1: Ingest real operator data (from Tunisie Telecom)
  - Phase 2: Engineer meaningful features from raw network + business data
  - Phase 3: Run AI models — predict SLA risk, detect anomalies, find correlations
  - Phase 4: Decision & Action Engine — evaluate results, generate recommendations with priority
  - Phase 5: Store everything — curated data + actions ready for consumption
- Color-coded phases: teal, blue, violet, red, green
- Visual: Use Diagram #3 (5-Phase Pipeline)

**Slide 5 — The Intelligence Layer: AI Models**
- Four AI components working together:
  - SLA Risk Prediction: "How likely is this region to breach SLA?" (score 0 to 1)
  - Network Anomaly Detection: "Is this cell behaving abnormally?"
  - Revenue Anomaly Detection: "Is subscriber revenue dropping unexpectedly?"
  - O+B Correlation: "When network degrades, what happens to revenue?"
- All outputs feed into the Decision & Action Engine
- Visual: Use Diagram #5 (ML Pipeline with Action Engine flow)

**Slide 6 — The Action Engine (What Makes Us L4)**
- This is what elevates us from analytics (L3) to autonomous agent (L4)
- The agent generates typed, prioritised action recommendations:
  - High SLA risk --> Proactive Alert (Critical)
  - Network anomaly + revenue drop --> Churn Prevention Campaign (High)
  - Healthy network + revenue spike --> Upsell Opportunity (Medium)
  - Cross-domain correlation found --> Insight Report for CVM (Low)
  - Multiple anomalies in same region --> Escalation Ticket (Critical)
- Actions have lifecycle: Generated --> Pending --> Approved/Dismissed
- Visual: Use Diagram #13 (Action Engine Rules)

**Slide 7 — Architecture Overview**
- 5 containerised microservices running in Docker Compose:
  - API Gateway (REST interface)
  - AI Service (ML models)
  - Pipeline Worker (orchestrates the 5 phases)
  - PostgreSQL (structured data store)
  - MinIO (3-layer data lake: raw / processed / curated)
- Cloud-portable: same Docker images deploy to Huawei Cloud Stack (ECS, OBS, RDS)
- Visual: Use Diagram #2 (Container Architecture) + Diagram #8 (HCS Mapping)

**Slide 8 — Data: Real Operator, Real Results**
- Working with real anonymised data from Tunisie Telecom
- Network data: cell performance KPIs across regions
- Business data: subscriber profiles, revenue, usage patterns
- Anonymised (hashed identifiers, no PII, gouvernorat-level only)
- Dual-mode: real data by default, synthetic fallback for demos
- 8-table database with full traceability (every result linked to its pipeline run)

**Slide 9 — What Makes Us Different**
- Comparison against existing solutions:
  - SELFNET: Self-healing 5G — no real data, no O+B convergence, no actions
  - ETSI ZSM: Zero-touch spec — specification only, not implemented
  - Nokia AVA: Telecom analytics — no O+B bridge, no autonomous actions
  - SmartCare (Huawei): CEM + demarcation — partial O+B, no autonomous actions
- Our project is the only one combining: Real Data + O+B Convergence + Cloud-Native + Autonomous Actions
- Visual: Use Diagram #17 (Competitive Comparison)

**Slide 10 — Outputs & Deliverables So Far**
- Working Docker stack (5 services, runs with one command)
- 3 trained ML models on real Tunisie Telecom data
- Decision & Action Engine generating typed recommendations
- Complete 3-layer data lake (raw, processed, curated)
- REST API for consuming results and managing actions
- 8-table PostgreSQL schema with full pipeline lineage
- Architecture designed for Huawei Cloud Stack deployment
- Documentation: technical report + architecture docs

**Slide 11 — Next Steps & Questions**
- Immediate: Finalise action engine rules with Huawei team feedback
- Short-term: Deploy to Huawei Cloud Stack (HCS) environment
- Medium-term: Real-time streaming, advanced ML (LSTM, transformers)
- Long-term: Reinforcement learning for action optimisation, path toward ADN L5
- Open for feedback and questions from supervisors
- "Thank you — Souhayl Guenichi | ESPRIT x Huawei Tunisia"

## PROMPT END

---
