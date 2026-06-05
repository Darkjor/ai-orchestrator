# ai-orch — AI Session Orchestrator

> A global, tech-agnostic CLI that keeps AI agents in sync across sessions.

## The problem

When multiple AI agents work on the same project — or a single agent returns after losing context — they repeat work, miss alerts, and make decisions that contradict earlier ones. `ai-orch` solves this with a structured `.ai/` folder that any agent can read in under a minute.

## Install

```bash
pip install ai-orchestrator
```

Or from source:

```bash
git clone <repo>
cd orquestador-v1
pip install -e .
```

## Quick start

```bash
# 1. Initialize in your project root
cd your-project
ai-orch init

# 2. Run triage at the start of every session
ai-orch triage

# 3. Install the pre-commit guard
ai-orch hook-install

# 4. At the end of each session, hand off
ai-orch handoff
```

## Commands

| Command | What it does |
|---------|-------------|
| `ai-orch init` | Creates `.ai/` folder with 7 context files |
| `ai-orch triage` | Shows active alerts, model recommendations, runs tests |
| `ai-orch check` | Pre-commit guard: fails if code changed but `.ai/` wasn't updated |
| `ai-orch hook-install` | Installs `ai-orch check` as a git pre-commit hook |
| `ai-orch handoff` | Interactive wizard to update `.ai/` docs and commit |

## The `.ai/` folder

| File | Purpose |
|------|---------|
| `CONTEXT.md` | Current project state — what works, what's broken, what changed |
| `ALERTS.md` | P0/P1/P2 issues — read before writing any code |
| `DECISIONS.md` | Architecture decisions log |
| `DISCUSSIONS.md` | Async threads between agents |
| `WHEELS.md` | Libraries tried and failed — don't reinvent |
| `ORCHESTRATOR.md` | Arrival protocol — every agent reads this first |
| `config.json` | Project metadata and model recommendations |

## Compatible with

Claude Code, Gemini CLI, Cursor, GitHub Copilot, GPT-4, and any AI tool that can read files.

## Requirements

- Python 3.10+
- Git repository

## License

MIT
