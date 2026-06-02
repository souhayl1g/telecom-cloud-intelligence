# GSD in Kimi — Command Reference & Operating Guide

> Offline reference for running **GSD (Get Shit Done)** inside **Kimi Code** on this repo.
> Source of truth: the 16 ported skills in `.kimi/skills/gsd-*/SKILL.md`. Last verified: 2026-05-29.
>
> **Syntax:** colon form — `/gsd:command [args] [--flags]` (NOT the dash form used by some docs).
> **Skill name ≠ command name.** You type verbs (`/gsd:new-project`), not skill folders (`gsd-project-init`).
> A command can appear in several skills (cross-reference); the **owner** skill is where its logic lives.

---

## TL;DR — the working loop for this project

You already ran `/gsd:map-codebase` (✓ `.planning/codebase/` has 7 maps). The GSD loop itself has **not** started
(no `PROJECT.md` / `ROADMAP.md` / `STATE.md` yet). Next moves:

```
# Protect CLAUDE.md first (see "Dual-tool danger" below), then:
/gsd:new-project            # or: /gsd:ingest-docs --mode new   (bootstrap from CLAUDE.md/AGENTS.md)
/gsd:discuss-phase 1        # lock decisions
/gsd:plan-phase 1           # goal-backward PLAN.md (+ auto plan-check)
/gsd:execute-phase 1        # implement, atomic commits, SUMMARY.md
/gsd:verify-work 1          # UAT against running code
# repeat per phase, then:
/gsd:ship
```

Lost the thread anytime → `/gsd:progress` routes you to the next action.

### Goal → command cheat sheet

| You want to… | Command |
|---|---|
| Analyze code (done) | `/gsd:map-codebase` (full) or `--fast --focus tech\|arch\|quality\|concerns` |
| Review code | `/gsd:code-review [--quick\|--deep] [--fix]` |
| Fix a non-obvious bug | `/gsd:debug` |
| Fix trivial error fast | `/gsd:fast [desc]` |
| Small tracked task | `/gsd:quick [desc] [--discuss --research --validate --full]` |
| Add a service / real feature | `/gsd:phase` → `/gsd:discuss-phase N` → `/gsd:plan-phase N` → `/gsd:execute-phase N` |
| Insert urgent work mid-roadmap | `/gsd:phase --insert <name>` or `/gsd:add-phase` |
| Enhance UI/UX | `/gsd:ui-phase N` then `/gsd:ui-review N` |
| Run all remaining phases | `/gsd:autonomous` |
| Where am I / resume | `/gsd:progress` · `/gsd:resume-work` · `/gsd:pause-work` · `/gsd:health` · `/gsd:stats` |

**Sizing rule:** trivial → `/gsd:fast`; small-but-track → `/gsd:quick`; real capability → a **phase**.
Mis-sizing (e.g. `/gsd:quick` on a 5-file feature) is the #1 GSD mistake.

---

## Full command reference (grouped by the 16 skills)

### 🔵 Core loop & lifecycle

#### `gsd-core-loop` — the 6-step spine
| Command | Does |
|---|---|
| `/gsd:new-project` | Start project: question → research → requirements → roadmap |
| `/gsd:discuss-phase N` | Lock decisions for a phase before planning |
| `/gsd:plan-phase N` | Goal-backward PLAN.md (owner = `gsd-planner`) |
| `/gsd:execute-phase N` | Implement plan, atomic commits (owner = `gsd-executor`) |
| `/gsd:verify-work N` | UAT against running code (owner = `gsd-verifier`) |
| `/gsd:ship` | Create PR, review, prep merge |

#### `gsd-project-init` — entry / config (command is `/gsd:new-project`)
| Command | Does |
|---|---|
| `/gsd:new-project [--auto @doc]` | Initialize (interactive, or auto from idea doc) |
| `/gsd:import` | Ingest external plans with conflict detection |
| `/gsd:config` · `/gsd:settings` | Workflow toggles, model profile |
| `/gsd:graphify` | Build/query project knowledge graph |
| `/gsd:resume-project` · `/gsd:resume-work` · `/gsd:pause-work` | Session continuity |
| `/gsd:progress` · `/gsd:health` | Where am I / planning-dir diagnostics |
| `/gsd:capture` | Zero-friction idea capture |

#### `gsd-phase-mgmt` — roadmap / milestone lifecycle
| Command | Does |
|---|---|
| `/gsd:phase [--insert\|--remove\|--edit] X` | CRUD phases in ROADMAP |
| `/gsd:new-milestone` · `/gsd:complete-milestone` · `/gsd:audit-milestone` | Milestone cycle |
| `/gsd:pr-branch` | Clean PR branch (filters out `.planning/` commits) |
| `/gsd:workspace` · `/gsd:workstreams` | Isolated workspaces / parallel streams |
| `/gsd:stats` · `/gsd:health` · `/gsd:progress` · `/gsd:resume-work` · `/gsd:pause-work` | Status & continuity |
| `/gsd:update` | Update GSD itself |

### 🟢 Planning & execution

#### `gsd-planner`
| Command | Does |
|---|---|
| `/gsd:plan-phase N [--gaps\|--reviews]` | Create/revise PLAN.md; auto plan-check |
| `ultraplan-phase` | Cloud-offload planning (beta) |

#### `gsd-executor`
| Command | Does |
|---|---|
| `/gsd:execute-phase N` | Wave-based parallel execution, per-task commits |
| `/gsd:quick [task]` | Small tracked task, skips roadmap |
| `/gsd:fast [task]` | Trivial inline fix, no subagents |

#### `gsd-fast-track` — sizing & exploration
| Command | Does |
|---|---|
| `/gsd:fast` | <2 min, one sentence |
| `/gsd:quick [--discuss --research --validate --full]` | Tracked small task |
| `/gsd:mvp-phase N` | Plan phase in MVP mode |
| `/gsd:spike [idea] [--quick --wrap-up]` / `spike frontier` | Throwaway experiment to validate |
| `/gsd:sketch [idea]` | Throwaway UI mockup |
| `/gsd:thread` | Persistent cross-session context threads |

#### `gsd-researcher` (mostly auto-spawned, not typed)
| Command | Does |
|---|---|
| `/gsd:ai-integration-phase` | AI design contract (AI-SPEC.md) |
| (auto-spawned by `/gsd:new-project`, `/gsd:plan-phase`, `/gsd:new-milestone`) | Domain / feasibility / comparison research |

### 🟣 Quality: review · debug · verify · UI

#### `gsd-code-reviewer`
| Command | Does |
|---|---|
| `/gsd:code-review [--quick\|--deep] [--fix]` | BLOCKER/WARNING/Info findings; `--fix` auto-patches |
| `/gsd:review` | Cross-AI peer review of plans |
| `/gsd:audit-fix` | Find → classify → fix → test → commit pipeline |
| `/gsd:audit-uat` · `/gsd:audit-milestone` | Outstanding-UAT / milestone audits |

Review depth ladder: `--quick` (grep, pre-commit) · `standard` (per-file, normal phase) · `--deep` (cross-file import/call graphs, security-critical only — expensive).

#### `gsd-debugger`
| Command | Does |
|---|---|
| `/gsd:debug` | Scientific-method debugging, persistent state across context resets |
| `/gsd:forensics` | Post-mortem of failed GSD workflows |

#### `gsd-verifier`
| Command | Does |
|---|---|
| `/gsd:verify-work N` | Conversational UAT → `N-UAT.md` |
| `/gsd:validate-phase N` | Nyquist validation audit → `VALIDATION.md` |
| `/gsd:eval-review N` | AI eval-coverage audit → `EVAL-REVIEW.md` |

#### `gsd-ui-ux`
| Command | Does |
|---|---|
| `/gsd:ui-phase N` | UI design contract (8-pt spacing, ≤4 font sizes, 60/30/10 color) |
| `/gsd:ui-review N` | Retroactive 6-pillar visual audit |
| `/gsd:sketch` · `/gsd:capture` | Mockups / idea capture |

### 🟠 Analysis & autonomy

#### `gsd-map-codebase`
| Command | Does |
|---|---|
| `/gsd:map-codebase [--fast --focus tech\|arch\|quality\|concerns]` | 7 codebase docs in `.planning/codebase/` |
| `/gsd:map-codebase --query <term>` / `status` | Query existing maps / freshness |

#### `gsd-autonomous`
| Command | Does |
|---|---|
| `/gsd:autonomous` | Run all remaining phases discuss → plan → execute |
| `/gsd:manager` | Interactive multi-phase command center |
| `/gsd:inbox` | GitHub issue/PR triage |
| `/gsd:add-todo` · `/gsd:check-todos` · `/gsd:note` · `/gsd:add-backlog` · `/gsd:capture` · `/gsd:add-phase` | Capture & backlog |

### ⚙️ Config & reference

#### `gsd-settings`
`/gsd:config` · `/gsd:settings` · `/gsd:surface`

#### `gsd-agents-reference` — catalog skill (documents commands whose logic lives elsewhere)
Notable: **`/gsd:ingest-docs`** → bootstrap `.planning/` *from* existing docs (your CLAUDE.md/AGENTS.md become the source).
Also lists: `/gsd:docs-update`, `/gsd:secure-phase`, `/gsd:update`, plus the core/quality commands.

#### `gsd-hooks`
Defines hook automation; references `/gsd:fast`, `/gsd:quick`, `/gsd:resume-work`, `/gsd:update`.

---

## `.planning/` artifacts (shared state)

| File | Purpose |
|---|---|
| `.planning/PROJECT.md` | Core value, constraints, current state, next milestone goals |
| `.planning/ROADMAP.md` | Phase structure, goals, success criteria, progress table |
| `.planning/REQUIREMENTS.md` | Scoped requirements + traceability |
| `.planning/STATE.md` | Current position, metrics, session continuity |
| `.planning/config.json` | Workflow mode, granularity, model profile, `claude_md_path` |
| `.planning/codebase/` | 7 codebase maps (STACK, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, CONCERNS, INTEGRATIONS) |
| `.planning/phases/phase-N/` | `PLAN.md`, `SUMMARY.md`, `CONTEXT.md` per phase |

Core principle: **Task completion ≠ Goal achievement.** A file can exist while the feature is broken — that's why
`/gsd:verify-work` checks the running code, not the SUMMARY's claims.

---

## ⚠️ Dual-tool danger: Claude Code + Kimi GSD on one repo

You work in Claude Code, run GSD in Kimi — **same repo, same `.planning/`, same `gsd-sdk` binary, same git history.**

1. **Never run both on the same files at once.** Both commit to git → merge hell. One tool at a time, or branch per tool.
2. **`/gsd:new-project` will touch your CLAUDE.md.** Kimi runtime resolves the instruction file to `CLAUDE.md`
   (verified `gsd-project-init/SKILL.md`: "Other runtimes → CLAUDE.md"). It **appends** GSD-managed sections and commits —
   non-destructive (never deletes), but bloats your hand-built CLAUDE.md and leaves `AGENTS.md` out of sync (breaks Rule 5).
   **Protect it — pick one:**
   - **Redirect:** set `"claude_md_path": "./CLAUDE.gsd.md"` in `.planning/config.json` so GSD writes its sections to a throwaway file.
   - **Back up + revert:** commit first, run GSD, then `git checkout CLAUDE.md AGENTS.md` to drop appended sections.
3. **`/gsd:ingest-docs --mode new`** is the doc-first alternative: it *reads* CLAUDE.md/AGENTS.md as the source and bootstraps
   `.planning/` from them (your docs stay authoritative). Use `--mode new` because `.planning/codebase/` already exists, which
   otherwise auto-routes to merge mode (degenerate with no ROADMAP/PROJECT yet).
4. **Your CLAUDE.md MANDATORY rules still apply in Kimi** — Kimi GSD's `gsd-planner`/`gsd-executor` enforce plan → approve → execute,
   aligned with Rule 1 (plan-first).
