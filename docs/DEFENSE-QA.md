# NeXo Defense — Full Report Q&A

**Source:** every question below is anchored to `report/main.pdf` (66 content pages, 9 chapters + 4 appendices). Answers quote the report's own framing — the jury reads the report, so your spoken answers must echo it, never contradict it.
**Verified against artefacts:** `notebooks/models/metrics.json`, `notebooks/models/rat_underservice_v3_model_card.md`, `notebooks/granger_feature_gate.json`, `dashboard/lib/tunisia-areas.ts`.

---

## 0. Numbers to know cold (self-test first)

| Fact | Value |
|---|---|
| Real BSS | **968,077** subscribers, Feb+Mar 2026, 26 features |
| Simulated BSS | **1.5M** (Jan/Apr/May, bootstrap + log-normal perturbation) → 2.47M total scored |
| Real OSS | **18.8M** cell-KPI rows (2G/3G/4G); +200K simulated reservoir |
| VAE training set | ~**500K** normal-only OSS records |
| CEM model | LightGBM-**DART**, 13 features, **256 leaves, depth 12** |
| CEM results | temporal **R²=0.9784**, MAE **0.0304**, RMSE 0.0322 (random: 0.9795 / 0.0309 / 0.0329) |
| VAE model | 9 features, **9→32→16→latent 8**, PyTorch GPU |
| VAE results | ROC-AUC **0.9821**, PR-AUC **0.9974** |
| RAT model | XGBoost, **19 leakage-free features**, depth **6**, lr 0.05, subsample 0.8, colsample 0.8, λ=1.0, γ=0.1, scale_pos_weight **1.52**, ≤800 rounds, early stop @799 |
| RAT results | temporal ROC-AUC **0.9203** / F1 **0.8927** · random 0.9419 / 0.8418 · 5-fold CV **0.9352** · PR-AUC 0.8912 · leakage alarm **0.995** |
| DSO targets | R²≥0.95 · ROC≥0.90 & recall≥0.70 · ROC≥0.90 · pairs at p<0.05 |
| Granger gate | **9 edges tested → 1 significant** (throughput→churn, median p=0.038); lag_max 4 months; ADF/KPSS + IC lag selection + Benjamini-Hochberg + reverse-Granger |
| Geography | **24 governorates + "Other" bucket = 25 buckets**; **26,071** distinct cell sites |
| Cycle time | real wall-clock **70 s – 3 min**, 2-minute daemon; never fabricated |
| L4 envelope | armed · confidence_threshold · playbook_whitelist (empty = nothing self-executes) · max_actions_per_hour · kill_switch |
| Auto-approval rule | needsHuman = (type == remediation) AND (severity ∈ {critical, warning}) |
| PSI thresholds | <0.10 stable · 0.10–0.25 moderate · >0.25 significant |
| Hardware | Ryzen 5 5600H · 24 GB RAM · RTX 3050 4 GB VRAM |
| Stack | Python 3.11 · FastAPI 0.115 · scikit-learn 1.5 · PyTorch 2.x · PostgreSQL 16 · Next.js 14 / React 18 · MLflow 2.x |

---

## 1. Opening questions (the first 3 minutes decide the room)

**Q: Present your project in two minutes.**
A: Memorize the arc: *"A mobile network is two networks living in the same place — the physical network the OSS watches, and the experience network subscribers live, which the operator only sees through the BSS. The pain: network anomalies are invisible to the OSS until a customer complaint reaches Care. I built NeXo, a cloud-native AI operations agent, at Huawei Tunisia on real anonymized Tunisie Telecom data. It converges OSS and BSS at the geographic-area level, scores experience with three ML models trained on ~2.5M subscriber records, proves statistically that network degradation leads experience drops via Granger causality, and closes the loop with an ADN Level-4 agent that auto-resolves safe actions and escalates risky ones — every decision audited."*

**Q: What is the single sentence pain?**
A: *"Network anomalies are invisible to the OSS until a customer complaint reaches Care."* (General Introduction — verbatim.)

**Q: What are your two research problems?**
A: **P1 — Convergence & anticipation:** can OSS KPI and BSS experience signals be converged so degradation is detected *before* the complaint? **P2 — Trustworthy autonomy:** can that intelligence drive an ADN L4 loop that auto-resolves safe actions and escalates risky ones, with a full audit trail? (§1.3.)

**Q: What are your three contributions?**
A: (1) **Statistical** OSS/BSS convergence via gated Granger testing — not co-visualization; (2) three production-grade models trained on real operator data, with explainability used as a *leakage guard* and temporal evaluation throughout; (3) a cloud-native platform with an auditable L4 autonomy layer closing the loop from detection to accountable action. (§2.10 + General Conclusion.)

**Q: Why the name NeXo?**
A: Internal codename for the convergence ("nexus") of the OSS and BSS worlds — the Network-Experience join. Keep it short; don't over-mythologize.

---

## 2. Chapter 1 — Context & Problem Statement

**Q: Why Huawei, and why does the placement matter?**
A: The internship was inside Cloud IT / Sales-Solution — the team that designs operational-intelligence solutions for regional operators. The work was framed from day one as a solution prototype aligned with Huawei's portfolio: the SmartCare CEM family and the ADN programme. Not a purely academic exercise. (§1.1.1.)

**Q: What is the difference between OSS and BSS?**
A: OSS is the network-facing world — per-cell counters: throughput, latency, packet loss, call-drop rate, signal power, cell load. BSS is the business-facing world — subscriptions, usage, devices, and the experience each subscriber receives. They evolved separately — separate vendors, schemas, teams — hence the blind spot. (§1.2.1.)

**Q: CEM vs CVM — and why did you scope to CEM?**
A: CEM measures and improves the *experience* a subscriber receives; CVM handles the *value* dimension — retention, churn, targeted intervention. NeXo is deliberately a CEM-oriented intelligence layer that feeds CVM decisions: it scores experience, detects degradation, surfaces at-risk subscribers, and leaves the commercial action to the operator. Revenue/billing is explicitly out of scope — the data is experience-oriented and CEM offers a richer ML surface. (§1.2.2.)

**Q: Where does SmartCare fit?**
A: SmartCare is Huawei's commercial CEM platform. Most deployed CEM systems lean on rule-based scoring — hand-tuned weighted thresholds. Transparent but brittle: they don't adapt to a new device mix and can't express non-linear interactions. NeXo keeps the CEM framing but replaces the rule engine with a learned regressor, recovering transparency through SHAP. (§2.1.)

**Q: What are the ADN levels and where do you sit?**
A: L0 manual · L1 assisted (tools visualize) · L2 partial (tools recommend) · L3 conditional (system decides, human supervises closely) · **L4 high autonomy — the system decides a bounded class alone, escalates the rest** · L5 full. Most operators sit at L2–L3; this project targets the jump to L4. The defining challenge of L4 is not model accuracy — it is *calibrated restraint*. (§1.2.3, Table 2.1, §2.8.)

**Q: "Your data is historical, not real-time — isn't that a fundamental limitation?"** *(expect this — the report pre-answers it)*
A: The objection mistakes the bottleneck. The pain is not data latency — it is **manual demarcation**: even with a perfect real-time feed, a human must still draw the boundary by hand — which area degrades, which subscribers it touches, whether network movement actually precedes the experience drop, and by how long. That demarcation is the analytical work NeXo automates: the geographic join, the anomaly isolation, the Granger lead-time. Because it is a structural problem, historical data demonstrates it fully; the method drops onto a live feed unchanged. *"Real-time ingestion is an engineering upgrade; automating the demarcation is the intellectual contribution."* (§1.3.1 — quote it.)

**Q: Trace one business objective to a measurable target.**
A: e.g. BO1 (detect degradation before Care) → DSO2: VAE anomaly detection with target ROC-AUC ≥ 0.90 and recall ≥ 0.70 → achieved 0.982. All four BO→DSO mappings are in Table 1.1 and revisited in Table 6.3. The point: every objective has a number, and every number is revisited — nothing is asserted without a check.

**Q: Why CRISP-DM and not Scrum/Kanban?**
A: The project's centre of gravity is data and models, and CRISP-DM's six phases map almost one-to-one onto the report's chapters. Modern engineering wasn't a competing methodology — it was absorbed into the Deployment phase: containers, versioned artefacts, metrics.json as source of truth, CI, observability. One methodology, coherent. (§1.5, Figure 1.2.)

**Q: What did YOU personally do vs. the team?**
A: The full stack: data profiling, feature engineering, training the three models, the leakage hunt, containerising the services, the dashboard, the L4 agent, the report. Weekly cadence with supervisors kept it aligned; §1.1.4 describes the three rhythms (conversations → data/modelling → software engineering).

---

## 3. Chapter 2 — State of the Art

**Q: Why is most published OSS/BSS convergence insufficient?**
A: It stops at *co-visualization* — a network dashboard next to an experience dashboard, leaving the human to infer the link. NeXo takes the harder step: **statistical convergence** — quantifying with a hypothesis test whether network KPI movements actually *precede* experience movements. That reframes convergence from a layout problem into an inference problem. (§2.2.)

**Q: Why not classical statistical anomaly detection (z-score, IQR, Mahalanobis)?**
A: Cheap and interpretable — we use them in EDA — but they assume a fixed, unimodal normality. Telecom KPI are multi-modal (a cell behaves differently at 3 a.m. and 9 p.m.), so a single global fence either misses real faults or floods the operator. (§2.3.1.)

**Q: Why not Isolation Forest?**
A: It handles multi-modality better and is a fine fast baseline (it remains our v2.0), but it treats each record independently and learns no compact representation of normal *joint* behaviour — it isolates outliers without modelling the manifold the inliers live on. That manifold is exactly what the experience-anomaly task needed. (§2.3.2.)

**Q: Why gradient-boosted trees for the two supervised tasks?**
A: They are the pragmatic state of the art on tabular data. LightGBM's histogram-based leaf-wise growth is fast and accurate on millions of rows; its DART variant injects dropout to curb late-tree overfitting. XGBoost offers a similarly regularised formulation with mature class-imbalance handling via scale_pos_weight. A deliberate split: DART for regression, XGBoost for classification. (§2.4, Table 2.2.)

**Q: Is Granger causality real causality?**
A: No — and the report says so itself. It is predictive precedence: X Granger-causes Y if past X improves prediction of Y beyond Y's own past. It rests on a stationarity assumption telecom KPI routinely violate, so we gate it: ADF/KPSS testing, information-criterion lag selection, Benjamini-Hochberg correction, reverse-Granger sanity check — and frame the output as a **directional hint, never proof**. That transparent framing is itself part of the contribution. (§2.5, §5.4.)

**Q: Why SHAP and not coefficients or permutation importance?**
A: SHAP assigns each feature a contribution to each *individual* prediction, grounded in cooperative game theory — turning the ensemble into a per-decision explanation. And we use it as a validation tool, not decoration: a wrongly important feature is often the first sign of leakage — which is exactly how the underservice trap was caught. (§2.6.)

**Q: What does Table 2.2 (technique selection) buy you?**
A: It shows every choice was made against alternatives, with criteria: rule engine/linear/GBR vs LightGBM-DART; z-score/IF/AE vs VAE; logistic/RF vs XGBoost; correlation-only/transfer entropy vs gated Granger; coefficients/permutation vs SHAP. If asked "why not X", point here first, then give the specific reason.

**Q: Your bibliography has only 9 references — is that thin?**
A: It's deliberately canonical: the primary sources of every technique used (Chandola anomaly survey, XGBoost, Granger 1969, LightGBM, Kingma & Welling VAE, Kleppmann, Lundberg SHAP, TM Forum ODA, Wirth CRISP-DM). One reference per pillar, cited at the exact point of use. Know which number maps to which technique.

---

## 4. Chapter 3 — Architecture & Design

**Q: Walk the C4 Level 1 context.**
A: NeXo sits between two data sources (OSS cell KPI, BSS subscriber records from TT production) and two roles: the NOC operator who consumes converged intelligence, and the autonomous agent acting under the operator's delegated authority. Care is a downstream beneficiary, not a user — the whole point is to decide *before* Care does. (§3.1.)

**Q: List the core containers and why this decomposition.**
A: api-gateway (FastAPI, REST+JWT+convergence), ai-service (3 models), auth-service (JWT/bcrypt/OAuth2), pipeline-worker (2-min ETL daemon), dashboard (Next.js 14), postgres 16 (system of record), minio (data lake), mlflow (tracking+registry), prometheus/grafana (observability), ollama (optional local LLM). The decomposition was chosen because the workload genuinely separates — ingestion, inference and UI have different lifecycles — not for fashion. (§3.2, Table 3.1.)

**Q: Why a gateway in front of the models?**
A: Three reasons: a single place to enforce JWT; freedom to retrain or relocate the model service without touching the front end; a natural home for the cross-cutting convergence queries joining network and business data. It costs one network hop and buys all three. (§3.2.1.)

**Q: Explain the three-layer data lake and why it matters.**
A: Raw (as received) → Processed (cleaned, typed, deduplicated) → Curated (analysis-ready feature tables). The value is reproducibility: any curated feature traces back through processed to the raw bytes — the audit trail a data-science defence requires. (§3.3.)

**Q: What is the "domain-scoped Converged Data Lake"?**
A: A deliberate small, faithful mirror of Huawei's Converged Data & AI Solution for Autonomous Networks. The industrial blueprint converges every operational source into one OceanStor/DLI lake; NeXo converges exactly two — OSS telemetry and BSS experience — narrower scope, same architecture. And the entire lake plus every model runs on-premises: confidential operator data never leaves the machine — the sovereignty property the blueprint treats as first-class. (§3.3.1.)

**Q: What is the Spatio-Temporal Convergence Layer?**
A: NeXo's equivalent of the blueprint's spatio-temporal digital twin. It answers *where* (the geographic join — 25 governorate buckets vs 26,071 distinct cell sites) and *when* (the Granger lag — how far an OSS cause leads its CEM effect). Exposed live on the /data-lake page; any value the system can't compute renders as a dash, never a fabricated zero. (§3.3.1.)

**Q: TRAP — "Tunisia has 24 governorates; your report says 25 buckets."**
A: Correct on both counts: 24 official governorates plus one "Other" bucket for records whose area couldn't be mapped — an honest engineering choice that keeps unmapped data visible instead of silently dropping it. (Mapping code normalises into the 24-governorate set + Other.)

**Q: Explain the run-centric schema.**
A: `pipeline_runs` is the parent table; model outputs (CEM scores, anomalies, underservice, correlations) and audit tables (agent actions, tickets, interventions) reference it by FK. Any cycle is fully reconstructible from a single run identifier — a reproducibility guarantee and the backbone of the L4 audit trail. (§3.4, Figure 3.4.)

**Q: Why is "cycle duration measured, never fabricated" in the report?**
A: Because a dashboard that shows instant cycles is decoration. A cycle does real work — sample, stage through the lake, infer, converge, persist — taking 70 s to 3 min wall-clock. The reported duration is measured from started_at to finished_at. It's an honesty invariant of the whole project. (§3.5.)

**Q: Why FastAPI / PostgreSQL / MinIO / Next.js?** *(one answer each, from §3.7)*
A: **FastAPI** — async model suits an I/O-bound gateway; automatic schema generation keeps the API contract accurate. **PostgreSQL** — the data is fundamentally relational (runs, scores, actions with strict FK), and JSONB stores semi-structured model explanations without abandoning integrity. **MinIO** — S3-compatible, so the lake speaks the same protocol a cloud object store would; the lift-and-shift path stays open. **Next.js** — its SSR model is precisely what solves the dashboard authentication problem (http-only cookie + server-side proxy).

**Q: Where does the LLM run — and does operator data leave the machine?** *(rehearse the reconciled answer)*
A: The language-model backend is **pluggable**: the orchestrator routes to a cloud provider (OpenRouter) when an API key is configured, and falls back to a fully local Qwen2.5 via Ollama otherwise. The deployed instance runs the cloud backend for response quality and latency; switching to local mode — a hard zero-egress guarantee for that channel — is a one-line configuration change, not a code change. Regardless of backend: the confidential TT data used to train and run the three ML models never leaves the local environment. (§3.7, §7.6, Appendix D — all three agree.)

**Q: Explain the security architecture.**
A: Layered, not perimeter. Auth-service verifies bcrypt credentials and issues JWT; every protected gateway endpoint validates it. The subtle problem was the dashboard: client components can't safely hold a secret, so the token lives in an http-only cookie the browser can't read, and a thin server-side proxy route attaches the bearer token when calling the gateway. The credential never enters client JavaScript — closing the most common SPA leak in one architectural stroke. (§3.8, §7.1.)

**Q: Authentication vs authorisation — how is the role enforced?**
A: The JWT carries the role (engineer / data scientist / admin). The gateway's `require_role` dependency re-validates it on every protected call — that's the real boundary. The dashboard's edge middleware uses the same role only to route personas — a convenience. A forged client role yields an empty page behind which every data request is refused. (§3.8, §7.8.)

**Q: Why MLflow over DVC/Prefect/ZenML?**
A: Three reasons specific to this stack: (1) one `autolog()` per framework covers LightGBM, PyTorch and XGBoost with no training-code changes; (2) its artifact store speaks S3 — the existing MinIO becomes the artifact backend with one env var, no new storage service; (3) its tracking database reuses the existing PostgreSQL. The registry makes promotion (Staging→Production) an explicit, auditable event, and CI validates that registered models exist and load before building. (§3.9.1.)

**Q: What makes the deployment "cloud-native" and portable?**
A: Declarative single docker-compose, standard containers, standard PostgreSQL, S3-compatible store — vendor-neutral on purpose. Named volumes persist state. The same composition lifts onto any orchestrator (ECS/CCE/K8s/Nomad) without rewriting application code: portability is a property of the architecture, not a provider dependency. (§3.6.)

---

## 5. Chapter 4 — Data

**Q: Inventory the data.**
A: BSS: 968,077 real (Feb+Mar 2026, 26 features) + 1.5M simulated (Jan/Apr/May). OSS: 18.8M real rows (2G/3G/4G counters) + 200K simulated temporal-drift reservoir. VAE trained on ~500K normal-only records drawn from the OSS corpus. (Table 4.1, abstract.)

**Q: What is the single most consequential fact about your data?**
A: The **asymmetry**: five BSS monthly snapshots (Jan–May, Feb+Mar real) but the OSS side anchored on a dense month at the time of the core modelling. Many subscriber months, few network months — this quietly shapes later decisions, above all the limited statistical power of the Granger analysis. (§4.2 — the report flags it explicitly; volunteer it before they find it.)

**Q: What was the most important EDA finding?**
A: The missingness map: four OSS "KPI" — cell load, jitter, packet loss, latency — arrived ~100% empty; only signal power (~2.5% missing) and throughput (~1%) were genuinely populated. Design decision: **derive, don't fabricate** — the missing KPI were computed from populated signals through documented physical relationships and labelled as derived throughout. The models learn from a mixture of measured and transparently-derived inputs, never invented numbers presented as measurements. (§4.2.1–4.2.2.)

**Q: How do you know the derived KPI are sensible?**
A: They inherit the physical structure of their measured parents — latency tracks inversely with throughput, packet loss rises where signal power falls (Figure 4.3). They are estimates, clearly labelled, and §6.7 names the inherited bias as a limitation.

**Q: Why winsorise outliers instead of dropping them?**
A: The outlier analysis showed the extremes are predominantly genuine heavy users, not corruption. Dropping them would delete real behaviour; winsorising preserves the signal while taming the leverage of a few extreme rows. (§4.2.4.)

**Q: What did the correlation analysis reveal before modelling?**
A: Two things: redundancy to prune (clusters of traffic-share measures) and — prophetically — a leakage risk: features that were really restatements of the target. That warning shaped the underservice feature set in Chapter 5. (§4.2.5.)

**Q: How was confidentiality handled?**
A: Subscriber identities reduced to irreversible hashes before ever reaching a model; the platform never stores or exposes a real IMSI or any directly identifying field; data never left the local environment — never uploaded, never committed (the directory is excluded by configuration), never shared; geographic analysis at governorate level, never the individual. Designed-in from day one, not bolted on. (§4.3.)

**Q: Justify the simulated months — isn't that making data up?**
A: The generator is firmly subordinate to the real data: bootstrap-resampling real records plus controlled log-normal perturbation and a small temporal drift, so simulated months inherit the real distributions rather than inventing new ones. Two validations: distribution overlays track the real shape (Figure 4.9), and a cross-month drift check confirms no spurious calendar signal (Figure 4.10). It's transparently labelled in Table 4.1 and bounded as a limitation in §6.7.

**Q: Why not a fancier generator (GAN, copulas)?**
A: Auditability. A bootstrap has no extra model to validate, preserves marginals and approximately the joint structure, and a jury can verify it against the real overlays. The cost — it can't create true new temporal dynamics — is exactly why the Granger power caveat exists.

**Q: What is the join key between OSS and BSS?**
A: The geographic area. There is no direct link between a subscriber identity and a single cell, so cell KPI are aggregated to the governorate — the key that joins the two worlds. This is also why area-level network-health features feed both the underservice classifier and the convergence engine. (§4.5, Figure 4.13.)

**Q: Name the engineered BSS features.**
A: Behavioural ratios shaped to be model-friendly: data intensity, attach success rates per generation (s1_mme_sr, iu_attach_sr, gb_attach_sr), the USIM-bottleneck flag — ratios and rates bounded by construction, skew tamed. (§4.5, Figure 4.11; full dictionaries in Appendix B.)

---

## 6. Chapter 5 — The Models

### CEM Experience Score (LightGBM-DART)

**Q: What is the task?**
A: Regression: given a subscriber's behavioural and network-context features, predict an experience score on a continuous 0–1 scale. It's the spine of the CEM layer — must be accurate and stable. (§5.1.1.)

**Q: Where does the target come from?** *(be ready — the report doesn't dwell on it)*
A: The score is a domain-defined composite built from the measured experience fields during data preparation — no measured QoE labels (NPS surveys, probe scores) exist in the feed, so the composite is the honest proxy. The model's value: scoring 2.47M subscribers per cycle in-pipeline, explaining drivers via SHAP, and being ready to swap in real QoE labels the day they exist. Note the result is 0.9784, not 1.0 — the model is not echoing a formula.

**Q: Explain gradient boosting in one breath.**
A: An additive ensemble built one stage at a time: each new tree fits the negative gradient of the loss left by the ensemble so far — it learns to correct the residual mistakes of everything before it. Functional gradient descent. (§5.1.2.)

**Q: Why DART over plain GBDT?**
A: Plain boosting lets late trees over-specialise on the dense centre of a skewed target. DART drops a random subset of existing trees each iteration, forcing new trees to remain broadly useful — it measurably improved generalisation to the held-out month. (§5.1.2.)

**Q: Configuration?**
A: 256 leaves, max depth 12, 13 engineered features — behavioural ratios (data intensity, USIM-bottleneck flag) plus area-aggregated network context. Evaluated under temporal hold-out: trained on earlier months, tested on a later one. (§5.1.3.)

**Q: How does OSS data enter the CEM model?** *(a subtle, strong question)*
A: Through the area aggregates: the 13 features include avg_throughput, avg_latency, avg_packet_loss and anomaly_rate — governorate-level network context, where anomaly_rate is itself the VAE's output. So convergence exists at the feature level too, not only in the Granger engine.

**Q: How do you know what the model learned is real?**
A: Two independent attribution methods agree: impurity-based global importance and mean-|SHAP| ranking tell the same story — behavioural intensity and network-context aggregates dominate, with the USIM-bottleneck flag contributing the sharp device-side signal it was engineered to capture. Two methods, one story — more likely to be real. (§5.1.4.)

### OSS Experience Anomaly (VAE)

**Q: What is the task and why unsupervised?**
A: No labelled network faults exist. We have a large body of normal OSS behaviour and must flag departures — anomaly detection by learning normality. (§5.2.1.)

**Q: Explain the VAE objective.**
A: It maximises the evidence lower bound (ELBO): a reconstruction term that rewards faithfully rebuilding the input from its compressed code, plus a KL regularisation term keeping the latent code close to a standard-normal prior. That regularisation is the edge over a plain autoencoder: the smooth latent space resists memorising noise, so the anomaly score generalises. (§5.2.2 — the report deliberately keeps it in prose.)

**Q: Architecture and training data?**
A: Encoder maps a 9-dimensional OSS experience vector (throughput, latency, packet loss, jitter, cell load, signal power, active users, integrity, call-drop rate) through hidden layers 32 and 16 to an 8-dimensional latent space; mirrored decoder. Trained on ~500K normal-only records on GPU. (§5.2.3.)

**Q: How was the anomaly threshold chosen?**
A: Not guessed — by sweeping the reconstruction-error distribution (Figure 5.5). The operating threshold sits in the valley between the normal and anomalous error populations (Figure 5.6); that visible separation is the geometric reason behind the precision-recall strength. (§5.2.3–5.2.4.)

**Q: Why is normal-only training a strength, not a weakness?**
A: You cannot know tomorrow's failure modes; training on labelled "anomalies" would overfit to yesterday's. Modelling normality flags *any* departure, including faults never seen before.

### RAT Underservice (XGBoost) — the leakage story

**Q: What is underservice?**
A: Subscribers who are 4G-capable but in practice remain stuck consuming 2G/3G traffic — prime churn risks and prime targets for intervention. (§5.3.1; the model card adds the operational motive: score subscribers when the formula inputs are unavailable, stale, or newly onboarded.)

**Q: Tell the leakage story — start to finish.** *(rehearse verbatim; it's your best story)*
A: An early version scored ROC-AUC ≈ 1.0. Near-perfection was not success — it was data leakage: `is_4g_capable` and `traffic_share_4g` were the label restated; the model was predicting an answer it had been handed. We removed not only the two direct inputs but every proxy that could reconstruct them — the other traffic-share variables, raw per-RAT traffic, data intensity, the highest-RAT field — leaving 19 leakage-free behavioural, device and area-context features. Then we added the standing integrity rule: **if random, temporal and CV all report AUC above 0.995, assume residual leakage and re-inspect.** The cleaned model scores 0.9203 temporal — and a defensible 0.92 is worth more than an unexamined 1.0. (§5.3.2, §6.7.)

**Q: XGBoost configuration?**
A: Depth-6 trees, learning rate 0.05, subsample and column-sample 0.8, L2 weight 1.0, minimum split-loss (gamma) 0.1, scale_pos_weight 1.52 for the class imbalance, up to 800 rounds with early stopping on validation AUC (stopped at 799). (§5.3.2 — matches the model card exactly; quote these, not any older document.)

**Q: Why XGBoost here and LightGBM for CEM?**
A: Both are valid boosted trees; the split was deliberate. The classifier needed XGBoost's mature imbalance handling via scale_pos_weight and its early-stopping behaviour for the leakage-hardened protocol; the regressor needed DART's dropout against the skewed target. Table 2.2 records the alternatives considered for each.

### Granger Causality engine

**Q: Explain the Granger F-test mechanically.**
A: Two nested linear regressions for a candidate effect series: a restricted model predicting it from nothing but its own lagged history, and an unrestricted model adding the lagged history of a candidate cause series. The F-test checks the joint significance of the added lagged terms: if they carry no real information, dropping them barely hurts the fit and we fail to reject the null; if they matter, the unrestricted model fits meaningfully better and the cause is flagged as Granger-causal. (§5.4.)

**Q: What is the null hypothesis?**
A: "The lagged values of the candidate cause add no predictive power for the effect beyond the effect's own lags." p below 0.05 → reject → the pair enters the gate.

**Q: Walk the two-tier architecture.**
A: Offline gate: test candidate network-to-experience pairs across the panel, keep the significant ones with their lags → `granger_feature_gate.json`. Online refresh: convert the selected lag into an operational lead time for the API and dashboard. Expensive statistics never run at serving time. (§5.4.)

**Q: What guards surround the raw test?**
A: ADF/KPSS stationarity testing, lag selection by information criterion, Benjamini-Hochberg correction across the tested edges, and a reverse-Granger sanity check. Because the panel has only a handful of months, the raw test has weak power — hence the full rigour wrapper and the "directional hint, never proof" framing. (§5.4.)

**Q: How many significant pairs did you find?** *(know the artefact truth)*
A: The gate tested 9 candidate edges and retained **1 significant pair** — throughput leading the experience/churn signal, median p = 0.038 — after correction. The report deliberately never quotes a count and frames the result as a directional hint: with few network months, honesty about statistical power matters more than an impressive number. As more network months accumulate, the engine gains power — that's the first perspective in the conclusion.

**Q: What does the forecast page actually compute?**
A: A lagged ordinary-least-squares projection over the significant OSS-to-CEM pairs — experience projected forward by the Granger-selected lag. Explicitly not a black-box time-series oracle. (§7.4.)

---

## 7. Chapter 6 — Evaluation & Results

**Q: What two principles govern your evaluation protocol?**
A: (1) Wherever temporal structure exists, temporal hold-out over random split — an operational model always predicts the future from the past, and a random split quietly leaks future information into training. (2) Report the metric that fits the task: R²/MAE/RMSE for regression; ROC-AUC + PR-AUC for the anomaly detector; ROC-AUC + F1 for the imbalanced classifier, cross-checked with stratified CV. (§6.1.)

**Q: Why is metrics.json such a big deal in your report?**
A: Every figure in Chapter 6 is read from a single generated artefact — `notebooks/models/metrics.json`, regenerated from the model cards. Nothing was typed by hand into a slide; if a model improves or regresses on retraining, the number moves with it. The dashboard reads the same file and fails loudly — 503 with remediation — rather than faking a fallback if it's missing. (Ch6 intro, §7.5.)

**Q: Interpret the CEM numbers.**
A: Temporal hold-out R² = 0.9784, MAE = 0.0304 on the 0–1 scale: the model explains ~98% of variance in subscriber experience and is wrong on average by about three points out of a hundred. The closeness of temporal and random splits (0.9784 vs 0.9795) is itself reassuring — the model isn't relying on calendar artefacts. Residuals are small, centred, no fanning — no heteroscedastic failure at the extremes. (§6.2.)

**Q: Which VAE metric matters more and why?**
A: PR-AUC (0.9974) over ROC-AUC (0.9821). When anomalies are rare, ROC lets the huge normal majority flatter the score; precision-recall doesn't. A PR-AUC near unity means: when the model raises an alarm, it is almost always right — exactly the property a NOC needs to trust an automated flag. (§6.3.)

**Q: The RAT temporal F1 (0.8927) is HIGHER than random-split F1 (0.8418) — isn't that suspicious?**
A: Unusual but welcome: it means the model generalises to a future month rather than degrading on it — the future month's class balance happens to suit the learned boundary. And the corroborating evidence is the CV ROC-AUC 0.9352 sitting comfortably below the 0.995 leakage alarm. A model in the low-to-mid nineties is far more credible than the leaky 1.0. (§6.4.)

**Q: Table 6.3 — did you meet all four DSOs?**
A: DSO1 met (0.978 ≥ 0.95), DSO2 met (0.982 ≥ 0.90), DSO3 met (0.920 ≥ 0.90), and DSO4 is reported honestly as a **directional hint**: significant pairs at p below 0.05 with identified lag were found, but the report downgrades the claim wording because the OSS-month scarcity caps statistical power. Choosing the honest word over the impressive one is the thesis of the whole chapter.

**Q: State your four limitations unprompted.** *(§6.7 — memorise)*
A: (1) **Network-month scarcity** — the deepest one; it caps Granger power, which is why the output is a hint, not proof. (2) **Derived KPI** — physically principled and labelled, but models inherit whatever bias the derivation carries. (3) **Simulated months** — validated against real distributions, but simulation never fully substitutes for production messiness. (4) **Leakage audits** — we caught one instance and designed checks for others, but no audit can prove total absence. Closing line: *"a defensible 0.92 with known limits is worth more than an unexamined 1.0."*

**Q: The low-score tail of the CEM distribution — why does it matter operationally?**
A: The clearly separated tail is what lets the actuation layer target interventions at a well-defined minority rather than the whole base — it's the bridge from a regression metric to a business action. (§6.2.)

---

## 8. Chapter 7 — Platform & L4 Autonomy

**Q: Why is the sidebar order a design decision?**
A: It's sequenced as a narrative — Start Here, Autonomy, Convergence, ML Models, Actuation — walking a first-time viewer from situational overview, to the autonomous hero feature, to the statistical convergence that justifies it, to the models underneath, to the actions the system can take. Not an alphabetical dump. (§7.2.)

**Q: Explain the auto-approval rule exactly.**
A: `needsHuman = (type == remediation) AND (severity ∈ {critical, warning})`. Everything else — informational actions and predictions, regardless of confidence — is auto-approved. Deliberately simple and auditable: conservative delegation, resolving what is safe and escalating what is not. Every action, auto or manual, is written to an immutable audit log with its full execution trace. (§7.6.)

**Q: Your classifier alone is only L3 — what makes it L4?** *(the sharpest ch7 question)*
A: Correct — a propose-but-human-closes system is conditional autonomy (L3). L4 requires acting unattended on trusted scenarios while the human controls the boundary rather than each decision. NeXo implements this as the server-enforced **closed-loop envelope**, one configuration record the operator owns: `armed` (master switch), `confidence_threshold`, `playbook_whitelist` (empty = nothing self-executes), `max_actions_per_hour`, `kill_switch`. When armed, each monitoring tick executes whitelisted, confident, non-rate-limited actions through the same playbook engine a human approval would use, stamping them `decided_by = L4-autonomous`. The conservative classifier becomes the L4 *exception path*; the envelope governs the delegated majority. Autonomy is a state the system can only enter once a human has explicitly granted scope. (§7.6.1 — rehearse this section word-for-word.)

**Q: What happens when the envelope refuses an action?**
A: The refusal is as explainable as an execution: skipped because the playbook isn't whitelisted, or because the hourly budget is spent — the exact reason is recorded. (§7.6.1.)

**Q: What are the agent's three faces?**
A: The conversational **NoC Mate** (natural-language operations through the pluggable LLM backend), the **Spirits & Decisions** view (the specialised agents — experience, network, action — plus the envelope above the human-approval queue), and the **playbooks + audit** views — the audit view being the trust anchor: a complete persisted history of every decision and why. (§7.6.)

**Q: Prove the actuation is real, not mocked.**
A: Tickets open in an internal NOC tracker with structured identifiers; notifications reach at-risk subscribers over SMS (console fallback when no gateway is configured); churn interventions act on the high-risk underservice population; the reporting playbook generates a capacity PDF into object storage behind a time-limited presigned link. Each writes an audit row — the same discipline as the agent itself. (§7.7.)

**Q: Describe the three personas and why RBAC is two-tier.**
A: Telecom Engineer (network surfaces, model results, convergence, actuation), Data Scientist (evaluation, notebook lab, data explorer, drift), Administrator (users/roles, settings, pipeline controls). The L4 agent is deliberately shared between the two operational roles — autonomy is the joint thesis. Enforcement: middleware routes personas (convenience); the gateway's `require_role` re-validates on every data request (boundary). Default-deny: a fresh account is an engineer until an admin grants more. A tampered client gains an empty shell. (§7.8.)

**Q: How does data-drift monitoring work?**
A: The Data Scientist view computes the Population Stability Index of each model feature across monthly snapshots against a baseline month — below 0.10 stable, 0.10–0.25 moderate, above 0.25 significant. Honest about its limits: a feature too degenerate to bin returns a dash, not a fabricated zero. (§7.9.)

**Q: Why rebuild Grafana/Jaeger/MinIO surfaces natively?**
A: The principle that nothing in the demonstration leaves the dashboard: metrics read the Prometheus API into in-house charts, traces render live OpenTelemetry spans, the object browser lists the three lake layers and signs short-lived links. One single pane — and because every surface is proxied through the same gateway with the same role checks, the security and honesty guarantees extend unchanged. (§7.9.)

---

## 9. Conclusion, Perspectives & Appendices

**Q: Answer P1 and P2 in one sentence each.**
A: P1: the models clear their targets and the gated Granger engine supplies a defensible lead-time signal — degradation becomes detectable upstream of the complaint. P2: the L4 agent enforces conservative, auditable delegation — safe auto-resolved, critical escalated, everything logged — and the actuation layer turns decisions into real, accountable operations. (General Conclusion.)

**Q: What three difficulties did you actually hit?**
A: The data asymmetry (many subscriber months, few network months — caps causal power); the leakage incident (a perfect score is more often a bug than an achievement); and operational discipline — keeping every metric tied to a generated artefact and every cycle to measured wall-clock time took constant vigilance against the temptation to fake a cleaner story. (General Conclusion.)

**Q: What are the three perspectives?**
A: (1) **Temporal depth** — more network months give Granger the power to graduate from hint to operational lead-time figure, and make a fourth model (LSTM churn-trajectory) trainable on the resulting sequences. (2) **The rolling-window engine** — replacing periodic batch sampling with a continuous stream, toward true real-time. (3) **Deployment scale** — vendor-neutral architecture lifts onto a managed cloud stack (Huawei's or any other) as an engineering exercise, not a redesign. (General Conclusion.)

**Q: Is the LSTM churn model built?**
A: No — planned, and explicitly so: it needs the accumulated sequence history. Never count it among delivered models; it's the first perspective.

**Q: Walk the six-month timeline.**
A: Month 1 business understanding; 1–2 data understanding; 2–3 data preparation; 3–4 modelling; 4–5 evaluation; 4–6 deployment — modelling and deployment deliberately overlapped because the data-preparation and engineering tracks fed each other. (Appendix A.)

**Q: Recite the three feature dictionaries.** *(Appendix B — at least know the shapes)*
A: **CEM (13):** usim_bottleneck, data_intensity, dou_total, duration, s1_mme_sr, iu_attach_sr, gb_attach_sr, avg_throughput, avg_latency, avg_packet_loss, anomaly_rate, generation_4g, generation_5g. **VAE (9):** jitter_ms, cell_load_pct, throughput_mbps, latency_ms, packet_loss_rate, rsrp_dbm, active_users, integrity, call_drop_rate. **RAT (19):** volte_flag, usim_flag, session_flag, dou_total, duration, voice_onlinetime_2g/3g, s1_mme_sr, iu_attach_sr, gb_attach_sr, attach_gap, and 8 area aggregates (avg_integrity/cdr/throughput/users/latency/loss_area, cell_count_area, anomaly_count_area). The platform loads these contracts from serialised artefacts at runtime — retraining with a wider feature set needs no code change.

**Q: What do s1_mme_sr / iu_attach_sr / gb_attach_sr mean?**
A: Attach success rates per radio generation's core interface: S1-MME for 4G, Iu for 3G, Gb for 2G. attach_gap is the spread between them — a device-behaviour signal.

**Q: Your whole platform runs on one workstation — is that a weakness?**
A: It's a deliberate proof point: an AMD Ryzen 5 5600H, 24 GB RAM, RTX 3050 4 GB — the reported GPU training times and the 2-minute cycle are representative of commodity hardware, not a data-centre. For the company, that's the argument: the OSS/CEM gap is closable with techniques that fit on commodity hardware. (Appendix D, General Conclusion.)

---

## 10. Trap questions & known weak spots (handle with care)

**T1 — "Figure 6.3's legend shows 0.9310, but you claim 0.9821. Which is it?"**
Five evaluation figures in ch5/ch6 are stale renders from an intermediate run (VAE panel, VAE PR curve, RAT panel, both feature-importance charts). The prose and tables are authoritative — every number there is regenerated from `metrics.json`. Best answer: *"The authoritative numbers are the tables — they are recomputed from the model artefacts by an automated dump, and three evaluation splits corroborate them. That figure is a stale render from an intermediate evaluation that we have flagged for regeneration."* **Action item: regenerate or remove those 5 figures before the defense if at all possible.**

**T2 — "Your models are trained mostly on simulated data."**
The real data anchors everything: the bootstrap resamples *from* the 968,077 real profiles and inherits their distributions (validated by overlay and cross-month drift checks); simulation only extends the time axis. The claim is always "968,077 real profiles + bootstrap-simulated months" — never a bare "2.5M real". And §6.7 names it as a limitation before you have to.

**T3 — "Does subscriber data leave Tunisia / the machine?"**
No absolute claim — give the precise truth: all structured data (BSS/OSS rows, the lake, the models) never leaves the local environment. The conversational channel's LLM backend is pluggable: cloud (OpenRouter) by default for quality, fully local Qwen2.5 via Ollama as a one-line switch when zero egress is required on that channel. (§3.7, §7.6, Appendix D agree.)

**T4 — "Is this deployed on Huawei Cloud Stack?"**
No. The architecture is cloud-portable (MinIO→OBS, PostgreSQL→RDS, containers→ECS/CCE, Ollama→ModelArts), and "HCS-Ready" means *portable by design* — never claim an actual HCS deployment.

**T5 — "Which comes first — convergence or training?"**
Both, at different layers. Data-layer convergence first: the geographic join key is built in data engineering (Ch4) — without it nothing downstream exists. Training next (Ch5): the CEM score doesn't exist as a raw column — it's a model output. Analytics-layer convergence last (§5.4, §6.5): the Granger engine tests whether OSS KPI series lead the CEM score series — which only exists after training and inference. In the current build, convergence does not feed back into training; closing that loop is the rolling-window perspective.

**T6 — "R² 0.9784 on a composite score — isn't that circular?"**
The target is a domain composite because no measured QoE labels exist — an honest proxy, and the model is not echoing it (0.9784, not 1.0; residuals unstructured). Its operational value is per-subscriber scoring at 2.47M scale per cycle plus SHAP drivers; the pipeline swaps in real QoE labels the day they exist.

**T7 — "Your Granger found only one significant edge — is the convergence thesis proven?"**
Frame it exactly as the report does: the engine proved the *method* — gated testing with stationarity checks, lag selection, multiple-comparison correction — and returned one significant pair at p = 0.038 under a handful of network months. The report deliberately reports a directional hint rather than overclaiming. The power limitation is a data-availability fact, and the first perspective (temporal depth) is precisely the remedy.

**T8 — "Why does the report avoid equations?"**
All mathematics is stated in prose (the boosting update, the ELBO terms, the Granger nested regressions). If asked: the report targets a mixed jury of engineers and business readers — every formal object is named and explained verbally (negative gradient, ELBO = reconstruction + KL, restricted vs unrestricted F-test). Be ready to write the actual formulas on the whiteboard if asked — that's the real test behind this question.

**T9 — "Report says depth-6 for XGBoost; other documents say depth-8/500 trees."**
The report and the model card agree (depth 6, lr 0.05, ≤800 rounds, early stop at 799). Older documents predate the leakage-hardened retrain. When in doubt: the model cards and metrics.json are the source of truth — the report was reconciled against them.

**T10 — "25 governorate buckets but Tunisia has 24 governorates."**
24 official + one "Other" bucket for unmapped records — nothing is silently dropped. (See Ch3 Q&A.)

**T11 — "Your abstract says ~500K OSS records but also 18.8M — contradiction?"**
No: 18.8M is the real OSS corpus; ~500K is the normal-only subset the VAE trained on. Different numbers, different objects — know which is which.

**T12 — "Did the university's similarity tool flag anything?"**
If asked: the report went through a typography pass that removed all flagged homoglyph characters (dashes, math symbols, Greek letters) — punctuation-only changes, zero prose changes; the final audit shows no non-ASCII characters outside the required French Résumé accents. Content originality was never the issue.

**T13 — "What happens if metrics.json is deleted?"**
The model-evaluation route returns 503 with a remediation message — a hard failure by design, never a hardcoded fallback. That's the honesty invariant applied to the UI. (§7.5.)

**T14 — "Can the L4 agent hallucinate an action?"**
The LLM only classifies intent and synthesises language. Execution is deterministic playbook code behind the envelope — whitelist, threshold, rate limit, kill switch, and human gate for critical/warning remediations. The model can phrase badly; it cannot act badly.

**T15 — "Why should a NOC trust this?"**
Because trust was engineered, not asserted: conservative auto-approval rule, operator-owned envelope, default-deny RBAC, every decision and refusal persisted with its execution trace, every metric traceable to an artefact, and limitations stated before they're asked. *"Autonomy is not a label the interface asserts but a state the system can only enter once a human has explicitly granted scope."* (§7.6.1.)

---

## 11. Final rapid-fire self-test (answer in ≤5 seconds each)

1. Pain hook? — *"Network anomalies are invisible to the OSS until a customer complaint reaches Care."*
2. CEM algorithm + headline metric? — LightGBM-DART, temporal R² 0.9784.
3. VAE headline metrics? — ROC-AUC 0.9821, PR-AUC 0.9974 (PR is the one that matters).
4. RAT three splits? — 0.9203 temporal / 0.9419 random / 0.9352 CV; alarm at 0.995.
5. Leakage features? — is_4g_capable + traffic_share_4g, plus all proxies removed.
6. Granger null? — lagged cause adds no predictive power beyond the effect's own lags.
7. Gate result? — 9 edges tested, 1 significant (throughput→churn, p=0.038); framed as directional hint.
8. L4 envelope fields? — armed, confidence_threshold, playbook_whitelist, max_actions_per_hour, kill_switch.
9. Auto-approval rule? — needsHuman = remediation AND (critical|warning).
10. Join key? — governorate (24 + Other); no IMSI↔cell link exists.
11. Real vs simulated? — 968,077 real BSS + 1.5M simulated; 18.8M real OSS + 200K.
12. Source of truth for metrics? — notebooks/models/metrics.json, regenerated from model cards.
13. Four limitations? — network-month scarcity, derived KPI bias, simulated months, leakage-audit bounds.
14. Three contributions? — statistical convergence, real-data models with explainability-as-guard, auditable L4 platform.
15. Three perspectives? — temporal depth (+LSTM), rolling-window engine, cloud lift.
