---
name: academic-defense-writer
description: "Write humanized academic content that passes plagiarism and AI detection. Actions: write, draft, rewrite, humanize, rephrase, improve writing, fix academic writing. Elements: thesis chapter, introduction, methodology, results, conclusion, abstract, defense presentation, report section, technical paragraph. Topics: ADN autonomous networks, CEM experience management, OSS/BSS convergence, ML model description, system architecture description, contribution statement."
---
# Academic Defense Writer — Humanized Engineering Report

## Core Principle
Every sentence must sound like it was written by a graduate engineering student who fully understands their work — not by an AI, not by copying a paper. The goal is: readable, personal, technically precise, and entirely original.

## Anti-Detection Rules (Plagiarism + AI Detection)

1. **Vary sentence length.** Mix short punchy sentences with longer analytical ones. Never write 3+ sentences of the same rhythm.
2. **Use first-person naturally.** "In this work, we designed...", "The approach we adopted...", "We observed that..."
3. **Ground every claim in the specific project.** Never write generic statements like "Machine learning is widely used". Write "In our context, GradientBoostingRegressor was chosen because..."
4. **Paraphrase source concepts in your own words.** When citing a technique, restate what it does in the context of this system, not a textbook definition.
5. **Include small imperfections of natural writing.** Transitional phrases like "It is worth noting that...", "Interestingly, the results showed...", "One key challenge we faced was..."
6. **Connect ideas causally.** Don't just list facts. Explain cause and effect: "Because the data is imbalanced..., we chose... which resulted in..."
7. **Include specific numbers and observations from the actual project** to ground the text in real results.

## Structure for Each Section

### Introduction / Context
- Open with the industrial problem (Tunisie Telecom context)
- Define the gap this project addresses
- State the contribution concisely (1-2 sentences)

### Methodology
- Explain the design choice *before* the implementation detail
- Use "we chose X because Y" pattern
- Reference actual architectural decisions: rolling window, 2-min pipeline cycles, 3-layer data lake

### Results
- Cite real metrics (R²=0.979, F1=0.877, etc.)
- Interpret what they mean for the telecom context
- Compare to baseline or alternative approaches

### Conclusion / Contribution
- Restate impact on CEM/CVM intelligence
- Frame within Huawei ADN paradigm
- Note limitations honestly (waiting for OSS data, synthetic data in phase 1)

## Technical Vocabulary for This Project
Use these naturally (not as a list dump):
- ADN (Autonomous Driving Network), L4 autonomy
- CEM (Customer Experience Management), SmartCare
- OSS/BSS convergence (O+B), Granger causality
- Rolling window engine, stratified sampling
- Experience anomaly, churn trajectory, RAT underservice
- Autoencoder, LSTM/GRU, GradientBoosting, IsolationForest
- HCS (Huawei Cloud Stack): OBS, RDS, ECS, ModelArts

## LaTeX Conventions (for final-defense-report/)
- Use `\cite{}` for all external references
- Figures: `\begin{figure}[htbp]` with descriptive `\caption{}`
- Use `\textit{}` for first introduction of technical terms
- Tables: `\begin{table}[h]` with `\toprule/\midrule/\bottomrule` (booktabs)
- Keep math in `equation` environment with proper notation

## Tone
Professional engineering report. Not formal-stuffy. Clear, confident, technically precise. The reader is a jury of engineers and academics — impress them with clarity, not vocabulary.
