---
name: nexo-defense-writer
description: Write academic thesis chapters and defense presentations for Telecom NeXoligence. Use when: (1) writing thesis chapters in AZ2021 LaTeX format, (2) creating defense slides (25-30 min), (3) describing CEM/SmartCare architecture, (4) explaining ML model methodology, (5) documenting cloud deployment, (6) writing contribution statements, (7) generating technical paragraphs about ADN, O+B convergence, or autonomous networks.
---

# NeXo Defense Writer

Write humanized academic content that passes plagiarism and AI detection for the NeXo project.

## Thesis Structure (9 Chapters)

| Chapter | Title | Content |
|---|---|---|
| 1 | Introduction | ESPRIT + Huawei internship context, objectives, project scope |
| 2 | Problem Context & Industrial Background | CEM/SmartCare, CVM, ADN paradigm, O+B convergence, Huawei NMS stack, Tunisian telecom market |
| 3 | State of the Art | Literature review: CEM platforms, anomaly detection, OSS-BSS convergence, cloud-native architectures |
| 4 | Architecture & Design | C4 diagrams, data flow, data lake, CEM→Agent→CVM positioning, HCS mapping |
| 5 | Implementation | Docker stack, pipeline-worker, AI service, API gateway, real data ingestion, anonymisation |
| 6 | AI Models & Training | GBR + IsolationForest v2.0, v3.0 models (LightGBM, VAE, CatBoost, TFT), feature engineering |
| 7 | Evaluation | Precision/recall/F1 per model, confusion matrices, correlation analysis, synthetic vs real comparison |
| 8 | Cloud Deployment | HCS deployment: OBS, RDS, ECS, VPC mapping + evidence screenshots |
| 9 | Conclusion & Perspectives | Summary, limitations, future work (real-time streaming, full SmartCare integration) |

## Writing Style Rules

1. **Humanization**: Vary sentence length. Use contractions sparingly. Insert occasional parenthetical asides.
2. **Technical depth**: Include specific hyperparameters (n_estimators=200, contamination=0.05). Reference actual file paths.
3. **Industrial framing**: Always tie back to Huawei ADN, SmartCare CEM, CVM, and Tunisie Telecom context.
4. **Data citation**: "Anonymised production data provided by Tunisie Telecom under collaboration agreement with Huawei Tunisia"
5. **Figures**: Every chapter needs at least one figure (architecture diagram, model chart, or results plot).

## Defense Presentation (25-30 min, ~25 slides)

1. Title + Context (1 min)
2. Problem + Industrial Gap (2 min)
3. State of Art (2 min)
4. Architecture — C4 L1 + L2 (4 min)
5. Data Lake + ETL (2 min)
6. AI Models v2.0 + v3.0 (4 min)
7. O+B Convergence Engine (2 min)
8. Dashboard + L4 Agent Demo (3 min)
9. Cloud Deployment Evidence (2 min)
10. Evaluation Results (2 min)
11. Contribution Statement (1 min)
12. Q&A

## Contribution Statement Template

> This project contributes a cloud-native AI Operations Agent that bridges CEM and CVM within Huawei's ADN paradigm. The three main contributions are: (1) a real-time O+B convergence engine correlating network KPIs with subscriber experience using statistical and causal methods, (2) four production-grade ML models trained on real Tunisie Telecom data for CEM scoring, anomaly detection, RAT underservice detection, and churn trajectory prediction, and (3) a containerized platform architecture validated for deployment on Huawei Cloud Stack.

## Key Files

- `final-defense-report/` — LaTeX thesis
- `report/` — Supporting reports and documentation
- `docs/architecture/` — C4 diagrams
- `docs/data-model/` — ER and data lake diagrams
- `notebooks/` — Model training evidence
