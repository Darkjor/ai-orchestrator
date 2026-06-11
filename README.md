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
| ------- | ------------ |
| `ai-orch init` | Creates `.ai/` folder with 8 context files |
| `ai-orch triage` | Shows active alerts, pending actions, model recommendations; scans for conflicts/secrets; runs tests |
| `ai-orch check` | Pre-commit guard: fails if code changed but `.ai/` wasn't updated, or WHEELS.md lint rules are violated |
| `ai-orch hook-install` | Installs the pre-commit guard and a post-commit snapshot refresher |
| `ai-orch handoff` | Interactive wizard to update `.ai/` docs and commit (`--snapshot` embeds a symbol map) |
| `ai-orch snapshot` | Injects an AST symbol snapshot of `src/` into `CONTEXT.md` |
| `ai-orch update` | Non-interactive section replace in any `.ai/` file (for agents) |
| `ai-orch action-add` | Records a manual action (DB/infra/other) in `PENDING.md` |
| `ai-orch action-resolve` | Marks a pending action as done (moves it to `## DONE`) |
| `ai-orch analyze` | Writes a verifiable metrics report to `.ai/ANALYSIS.md` |
| `ai-orch qa` | Cross-checks the analysis against live state; escalates discrepancies |
| `ai-orch export` | Bundles all `.ai/` files into one Markdown document (stdout or `--out`) |
| `ai-orch observe` | Shows recent agent-run metrics from the optional Supabase store |

Architecture and data contracts for contributors (human or AI): [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md).

## The `.ai/` folder

| File | Purpose |
| ---- | ------- |
| `CONTEXT.md` | Current project state — what works, what's broken, what changed |
| `ALERTS.md` | P0/P1/P2 issues — read before writing any code |
| `DECISIONS.md` | Architecture decisions log |
| `DISCUSSIONS.md` | Async threads between agents |
| `WHEELS.md` | Libraries tried and failed — don't reinvent |
| `PENDING.md` | Manual actions: DB migrations, infra tasks (with action-add/action-resolve) |
| `ORCHESTRATOR.md` | Arrival protocol — every agent reads this first |
| `config.json` | Project metadata and model recommendations |

## Real-world examples

### Multi-agent handoff workflow

When Agent A runs out of tokens mid-task, Agent B takes over cleanly:

**Agent A (ending session):**
```bash
# Update CONTEXT.md with exactly where work stopped
ai-orch update --section "Current State" --value "- Refactored authentication module; stopped at JWT refresh token caching"

# Document what was learned
ai-orch update --section "Most recently changed" --value "- src/auth.py: added token validation"

# Create or resolve alerts
ai-orch action-add "Cache refresh tokens in Redis" --type infra --target "Redis cluster"

# Handoff with git commit
ai-orch handoff
```

**Agent B (arriving at project):**
```bash
# Follow arrival protocol (auto-read by .ai/ORCHESTRATOR.md)
ai-orch triage                  # See all P0/P1/P2 alerts and model recommendations
cat .ai/CONTEXT.md             # Understand where Agent A stopped
cat .ai/ALERTS.md              # Check critical blockers

# Continue work from exact stopping point
# See .ai/PENDING.md for manual tasks
ai-orch action-resolve DB-001  # Mark completed actions as done
```

### GitHub Actions integration

Run triage on every PR to catch issues early:

```yaml
# .github/workflows/ai-orch-triage.yml
name: AI Orchestrator Triage
on: [pull_request]

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install ai-orchestrator
      - run: ai-orch triage
      - run: ai-orch check  # Verify .ai/ was updated with code changes
```

### Custom template scenario

Customize model recommendations for your project stack:

```bash
ai-orch init

# Edit .ai/config.json to match your team's workflow
```

Example `.ai/config.json` with task-specific models:

```json
{
  "project_name": "payment-api",
  "project_type": "backend",
  "stack": "Python 3.11, FastAPI, PostgreSQL, Stripe",
  "test_command": "pytest tests/ -v",
  "models": {
    "default": "claude-sonnet-4-6",
    "recommendations": {
      "architecture": "claude-opus-4-8",
      "code_review": "claude-opus-4-8",
      "refactoring": "claude-sonnet-4-6",
      "bugfix": "claude-sonnet-4-6",
      "feature": "claude-sonnet-4-6",
      "tests": "claude-sonnet-4-6",
      "docs": "claude-haiku-4-5-20251001"
    },
    "reasoning_tasks": ["architecture", "code_review"]
  }
}
```

## API usage

Import `ai-orch` helpers into your own Python scripts. Since v0.3 the logic lives in
single-responsibility domain modules (`aiorch.alerts`, `aiorch.pending`,
`aiorch.context`, ...); `aiorch._helpers` remains as a stable re-export shim, so both
import styles work:

```python
from aiorch.alerts import parse_alerts
from aiorch.pending import parse_pending
from aiorch.context import update_section

# Check for active alerts in a project
alerts = parse_alerts(".ai/ALERTS.md")
for alert in alerts:
    print(f"{alert['id']}: {alert['title']} ({alert['severity']})")

# Check pending manual actions
actions = parse_pending(".ai/PENDING.md")
for action in actions:
    print(f"{action['id']}: {action['title']}")

# Update context sections programmatically
update_section(".ai/CONTEXT.md", "Current State", "- New finding from analysis")
```

See [docs/API.md](docs/API.md) for full API documentation.

## Troubleshooting

**Q: `.ai/ folder not found` error**

Run `ai-orch init` in your project root. This creates the `.ai/` folder with all 8 context files.

**Q: JSON parsing fails in triage**

Ensure `.ai/config.json` is valid JSON. Use a JSON linter or check for trailing commas.

**Q: Git hook conflicts on Windows**

The hook is shell script format. On Windows, ensure Git Bash or WSL is installed. The hook auto-detects and calls either `ai-orch` or `python -m aiorch.main`.

**Q: Permission denied on `.git/hooks/pre-commit`**

Run `chmod +x .git/hooks/pre-commit` after `ai-orch hook-install`.

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more issues and solutions.

## Compatible with

Claude Code, Gemini CLI, Cursor, GitHub Copilot, GPT-4, and any AI tool that can read files.

## Requirements

- Python 3.10+
- Git repository

## License

MIT
