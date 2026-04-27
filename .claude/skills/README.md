# NeXo Skill Registry

All skills available for the Telecom NeXoligence project.

## Trigger Map

| When the user asks for... | Use Skill |
|---|---|
| Write thesis chapter, defense slides, academic report, contribution statement | `academic-defense-writer` |
| Design FastAPI endpoint, Docker service, PostgreSQL query, CI/CD pipeline | `cloud-native-ai` |
| Explain how code works, walk through algorithm, review before refactoring | `explain-code` |
| Train ML model, evaluate metrics, feature engineering, model deployment | `mlops-python` |
| Design dashboard UI, choose colors/fonts, review React/Next.js code | `ui-ux-pro-max` |
| Generate simulated BSS data, bootstrap sampling, month drift | `nexo-bss-simulator` |
| Train v3.0 models (LightGBM, VAE, CatBoost, TFT), inference endpoints | `nexo-ml-trainer` |
| Deploy to HCS, SWR push, ECS tasks, OBS/RDS config, evidence collection | `nexo-hcs-deployer` |
| Write thesis chapters, defense slides for NeXo specifically | `nexo-defense-writer` |
| Deep research on any topic, academic references, literature review | `research-codex-en` |

## Skill Directory

```
.claude/skills/
├── academic-defense-writer/    # Humanized academic writing
├── cloud-native-ai/            # FastAPI, Docker, PostgreSQL, CI/CD patterns
├── explain-code/               # Educational code breakdown
├── mlops-python/               # scikit-learn, PyTorch, model training
├── ui-ux-pro-max/              # Dashboard design, React/Next.js UI
├── nexo-bss-simulator/         # BSS bootstrap generation + OSS simulation
├── nexo-ml-trainer/            # v3.0 model training pipeline
├── nexo-hcs-deployer/          # Huawei Cloud Stack deployment
├── nexo-defense-writer/        # Thesis + defense for NeXo
└── research-codex-en/          # Academic research and references
```

## Usage

Skills auto-trigger based on user request matching the skill `description` field.
For precise triggering, reference the skill name directly: "use the nexo-ml-trainer skill to..."
