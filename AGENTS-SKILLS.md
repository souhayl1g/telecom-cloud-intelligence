# NeXo Agent Skills — Installation Guide
## For: Claude Code, Kimi Code CLI, Gemini CLI, Copilot CLI, and all agents

> Last updated: 2026-06-10
> Project: Telecom Cloud Intelligence (NeXoligence)
> Owner: Souhayl Guenichi

This file is the single source of truth for all agent skills in this project.
**Install all skills before working on this codebase.** Each skill encodes project-specific
domain knowledge that no general-purpose agent has by default.

---

## Quick Install — All Skills At Once

```bash
# From the project root — installs all project skills for Claude Code
npx skills add practicalswan/agent-skills --skill pptx --skill security-review -y
npx skills add dylantarre/animation-principles --skill data-visualization --skill micro-interactions -y
```

The project-specific skills (nexo-*, mlops-python, cloud-native-ai, etc.) are already in
`.agents/skills/` and `.claude/skills/` — they install automatically via `skills-lock.json`:

```bash
npx skills experimental_install
```

---

## Full Skills Inventory (15 project-level skills)

### Domain & Architecture Skills

| Skill Name | Trigger Keywords | When to Use |
|------------|-----------------|-------------|
| `cloud-native-ai` | FastAPI, Docker, PostgreSQL, MinIO, CI, auth | Any change to api-gateway, pipeline-worker, docker-compose, auth-service |
| `mlops-python` | train, model, sklearn, pytorch, joblib, inference | Touching ML code, retraining, pipeline steps, ai-service endpoints |
| `nexo-ml-trainer` | LightGBM, VAE, XGBoost, CEM score, anomaly, RAT | Training or evaluating the 3 v3.0 models |
| `nexo-bss-simulator` | simulate, generate BSS, sample BSS, synthetic data | Generating simulated subscriber data |
| `nexo-hcs-deployer` | HCS, Huawei Cloud, OBS, RDS, ECS, deploy | Cloud deployment evidence, HCS mapping |

### Writing & Defense Skills

| Skill Name | Trigger Keywords | When to Use |
|------------|-----------------|-------------|
| `nexo-defense-writer` | thesis, chapter, defense, slides, academic, write | Writing thesis chapters, defense content, technical paragraphs |
| `academic-defense-writer` | humanize, AI detection, academic writing, rephrase | Rewriting for plagiarism/AI detection bypass |
| `pptx` | PowerPoint, .pptx, slides, presentation, python-pptx | Generating actual .pptx files for defense day |

### UI / Frontend Skills

| Skill Name | Trigger Keywords | When to Use |
|------------|-----------------|-------------|
| `ui-ux-pro-max` | design, UI, component, glassmorphism, layout, color | Any dashboard design work, component building |
| `data-visualization` | chart, graph, animate chart, D3, data viz | Making charts distinctive and animated |
| `micro-interactions` | hover, click feedback, animation, transition, feel | Adding micro-animations that make UX "different" |

### Security & Quality Skills

| Skill Name | Trigger Keywords | When to Use |
|------------|-----------------|-------------|
| `security-review` | security, audit, vulnerability, injection, secrets | Pre-commit security check, before any release |

### Research & Discovery Skills

| Skill Name | Trigger Keywords | When to Use |
|------------|-----------------|-------------|
| `research-codex-en` | research, find, study, literature, compare | Deep research on any topic |
| `explain-code` | explain, what does this do, how does X work | Explaining codebase to new contributors |
| `find-skills` | find skill, skill for X, install skill | Discovering new skills from the marketplace |

---

## Project Context (Critical — Read Before Acting)

This is the **NeXoligence** platform: cloud-native AI ops for Tunisie Telecom CEM intelligence.

### Architecture at a Glance
```
api-gateway :8000    → FastAPI, all public endpoints, JWT-protected
ai-service  :8001    → 3 ML models (LightGBM, VAE, XGBoost) v3.0
auth-service:8002    → JWT + bcrypt, SMTP password reset
pipeline-worker      → 22-step daemon, 2-min cycles
dashboard   :3001    → Next.js 14, App Router, TypeScript
postgres    :5432    → PostgreSQL 16, pgdata volume persists
minio       :9000    → 3-layer data lake (raw/processed/curated)
```

### Mandatory Rules (ALL agents must follow)
1. **Plan first** — no code before a written plan is approved
2. **No fake data** — missing values render as `'—'`, never `0.0` or synthetic zeros
3. **Time = Africa/Tunis (UTC+1)** — use `dashboard/lib/time.ts` utils only
4. **Feature contract = the joblib** — never hardcode feature lists in routers
5. **CLAUDE.md = AGENTS.md** — these two files must stay byte-identical after any edit
6. **Verify before done** — restart the service, hit the endpoint, see the real response

### Stay Lean Rule (Skills)
- Cap: ~15 project-level skills max
- Remove skills not used in 2+ weeks of active work
- Before adding: check install count ≥500, verify source reputation, read SKILL.md content
- See: `.claude/projects/.../memory/skills_workflow.md` for the full security-audit protocol

---

## Defense Day Context (mid-July 2026)
- Advisor rehearsal: next week (1-on-1, 20 min)
- Final defense: mid-July 2026, ESPRIT jury
- Speaking guide: `docs/DEFENSE-SPEAKING-GUIDE.md`
- PPTX target: 18 slides, hybrid dark/light theme, Plus Jakarta Sans font
- Pain hook (slide 2): *"Network anomalies invisible to OSS until customer complaint reaches Care."*

---

## Kimi Code — Specific Instructions

Kimi Code uses the `.agents/skills/` directory. Skills are auto-symlinked during install.
To verify Kimi can see the skills:

```bash
# Check skills are in the universal agents directory
ls .agents/skills/

# Re-sync if missing
npx skills experimental_sync -y
```

All skills in this project were installed with `--agent '*'` flag, meaning they are available
to Kimi Code, Gemini CLI, GitHub Copilot, Claude Code, and Amp simultaneously.

---

## Skills Lock

`skills-lock.json` at the project root tracks exact skill versions.
Run `npx skills experimental_install` to restore the full stack on a fresh clone.
