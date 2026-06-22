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
| `ai-orch init` | Creates `AGENTS.md` at the project root + `.ai/` folder with 6 context files, auto-detecting the project's name/stack/commands |
| `ai-orch triage` | Shows active alerts, model recommendations, runs tests |
| `ai-orch check` | Pre-commit guard: fails if code changed but `AGENTS.md`/`.ai/` weren't updated |
| `ai-orch hook-install` | Installs `ai-orch check` as a git pre-commit hook |
| `ai-orch handoff` | Interactive wizard to update `.ai/` docs and commit |

## Agent instructions

`ai-orch init` writes `AGENTS.md` to your project root — the open format already adopted by 25+ AI coding tools (Codex, Cursor, Copilot, Windsurf, Claude Code, and more), governed by the Linux Foundation's Agentic AI Foundation. No proprietary file for agents to learn; if `AGENTS.md` already exists, `init` leaves it untouched.

## The `.ai/` folder

What `AGENTS.md` and architecture-decision tooling don't already give you:

| File | Purpose |
|------|---------|
| `CONTEXT.md` | Current project state — what works, what's broken, what changed |
| `ALERTS.md` | P0/P1/P2 issues — read before writing any code |
| `DECISIONS.md` | Architecture decisions log |
| `DISCUSSIONS.md` | Async threads between agents |
| `WHEELS.md` | Libraries tried and failed — don't reinvent |
| `config.json` | Project metadata and model recommendations |

## Compatible with

Any AI tool that reads `AGENTS.md` (Claude Code, Codex, Cursor, GitHub Copilot, Windsurf) plus any tool that can read files for the `.ai/` docs (Gemini CLI, GPT-4, etc).

## Requirements

- Python 3.10+
- Git repository

## License

MIT
