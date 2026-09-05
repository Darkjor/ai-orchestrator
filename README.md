# ai-orch — AI Session Orchestrator

> A global, tech-agnostic CLI that keeps AI agents in sync across sessions.

## The problem

When multiple AI agents work on the same project — or a single agent returns after losing context — they repeat work, miss alerts, and make decisions that contradict earlier ones. `ai-orch` solves this with a structured `.ai/` folder that any agent can read in under a minute.

## Install

From GitHub (recommended until the PyPI release):

```bash
# Install the v0.3.0 release
pip install "git+https://github.com/Darkjor/ai-orchestrator.git@v0.3.0"

# Update an existing install (any machine) to the latest master
pip install -U "git+https://github.com/Darkjor/ai-orchestrator.git@master"
```

Or from a local clone:

```bash
git clone https://github.com/Darkjor/ai-orchestrator.git
cd ai-orchestrator
pip install -e .
```

### Works in any IDE

`ai-orch` is a CLI and a folder of Markdown, so it works anywhere. Two commands make
that explicit:

```bash
ai-orch ide-install     # AGENTS.md + .agents/rules/ai-orch.md
ai-orch brief --out STATUS.md
```

`ide-install` writes an `AGENTS.md` — read automatically by **Google Antigravity**
(1.20.5+), Cursor and Copilot — plus an Antigravity workspace rule with
`trigger: always_on`, that IDE's nearest equivalent to a session-start hook. Both are
written as a managed block between `<!-- ai-orch:start -->` markers, so regenerating
never touches text you wrote around it.

`brief` renders the live `.ai/` state as one page aimed at **humans**: what is
happening now, what is broken, what needs a person, where the detail lives. Point it at
a discoverable path and teammates get the project's status in their IDE's Markdown
preview without ever running the CLI.

The git hooks are IDE-agnostic by construction — they run at `git commit`, so the guard
works identically in Antigravity, VS Code, or a bare terminal.

### Claude Code plugin (optional)

The repo doubles as its own Claude Code marketplace. Installing the plugin teaches
Claude the arrival/handoff rituals and injects an arrival brief at session start:

```
/plugin marketplace add Darkjor/ai-orchestrator
/plugin install ai-orch@ai-orch
```

You still need the CLI (`pip install ...` above) — the plugin drives it, it does not
replace it. It adds four skills (`/ai-orch:ai-orch`, `/ai-orch:arrival`,
`/ai-orch:handoff`, `/ai-orch:pipeline`) and a `SessionStart` hook that prints open P0/P1 alerts and pending
manual actions into the agent's context. In a project with no `.ai/` folder the hook
prints nothing.

## Quick start

```bash
# 1. Initialize in your project root
cd your-project
ai-orch init

# 2. Run triage at the start of every session
ai-orch triage

# 3. Install the pre-commit guard
ai-orch hook-install

# 4. Teach other IDEs the protocol (Antigravity, Cursor, Copilot)
ai-orch ide-install

# 5. At the end of each session, hand off
ai-orch handoff                          # human at the keyboard
ai-orch sync --note "where you stopped"  # agent, unattended
```

## Commands

| Command | What it does |
| ------- | ------------ |
| `ai-orch init` | Creates `.ai/` folder with 8 context files |
| `ai-orch triage` | Shows active alerts, pending actions, model recommendations; scans for conflicts/secrets; runs tests |
| `ai-orch check` | Pre-commit guard: fails if code changed but `.ai/` wasn't updated, or WHEELS.md lint rules are violated |
| `ai-orch hook-install` | Installs the pre-commit guard and a post-commit snapshot refresher |
| `ai-orch handoff` | Interactive wizard to update `.ai/` docs and commit (`--snapshot` embeds a symbol map) |
| `ai-orch sync` | **Non-interactive handoff for agents** — you pass `--note` (the why), git supplies the changed files (the what) |
| `ai-orch snapshot` | Injects an AST symbol snapshot of `src/` into `CONTEXT.md` |
| `ai-orch update` | Non-interactive section replace in any `.ai/` file (for agents) |
| `ai-orch action-add` | Records a manual action (DB/infra/other) in `PENDING.md` |
| `ai-orch action-resolve` | Marks a pending action as done (moves it to `## DONE`) |
| `ai-orch analyze` | Writes a verifiable metrics report to `.ai/ANALYSIS.md` |
| `ai-orch qa` | Cross-checks the analysis against live state; escalates discrepancies |
| `ai-orch export` | Bundles all `.ai/` files into one Markdown document (stdout or `--out`) |
| `ai-orch brief` | Renders `.ai/` as one human-readable status page for teammates browsing the repo |
| `ai-orch ide-install` | Writes `AGENTS.md`, `CLAUDE.md` `@imports` and `.agents/rules/` so every IDE learns the protocol |
| `ai-orch validate` | Validates a structured inter-agent envelope before it is passed on (`--role` pins the sender) |
| `ai-orch roles` | Lists agent role prompts and their versions |
| `ai-orch observe` | Shows recent agent-run metrics from the optional Supabase store |

`ai-orch` itself only records `latency_ms` and `status` for `analyze` and `qa` (including `override_approved` on a human override). The `tokens_in`/`tokens_out`/`cost_usd`/`eval_score` columns are populated by your own agents calling `SupabaseLogger.log_run(...)` directly — `observe` just renders whatever the table holds.

* Para documentación detallada y en español, consulta el [Manual de Usuario](docs/MANUAL.md).
* Architecture and data contracts for contributors (human or AI): [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md).

## Multi-agent pipelines

When more than one agent works a task, prose between them is the failure point:
the receiver has to *interpret*, and interpretation is where hallucination enters.
`ai-orch` defines a structured envelope instead, and validates it at the boundary.

```
planner ──▶ executor ──▶ qa ──┬─▶ executor   (rejected: another pass)
                              └─▶ none       (approved: chain ends)
```

```bash
ai-orch validate envelope.json --role executor
```

Exit 0 prints the routing decision; exit 1 lists every violation at once with the
exact field path, so an agent fixes them in one pass rather than one round-trip
per field. The contract enforces role-specific required fields, legal transitions
(nothing routes back to the planner, so a chain cannot loop forever), that a step
carries a verifiable `done_when`, that `status: "ok"` cites evidence, and that QA
cannot approve while a P0 finding stands.

Role prompts live in `.ai/config.json` and are versioned like code:

```bash
ai-orch roles     # every role and its prompt version
```

The full standard — decomposition, structured chaining, which prompting habits are
now hard API errors, prompt versioning, and why QA stays fresh — is in
[skills/pipeline/SKILL.md](skills/pipeline/SKILL.md).

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
# One command: you supply the why, git supplies the what.
# `sync` never prompts — unlike `handoff`, which is an interactive wizard
# and will hang an unattended agent.
ai-orch sync --note "Refactored authentication module; stopped at JWT refresh token caching"

# Record work only a human can do
ai-orch action-add "Cache refresh tokens in Redis" --type infra --target "Redis cluster"

git add -A && git commit -m "refactor: auth module"
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

> `handoff` and `qa` prompt on stdin — they are for humans. Agents use `sync`,
> `update`, `action-add` and `analyze`, none of which block.

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
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - run: pip install "git+https://github.com/Darkjor/ai-orchestrator.git@v0.3.0"
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
    "default": "claude-sonnet-5",
    "recommendations": {
      "architecture": "claude-opus-5",
      "code_review": "claude-opus-5",
      "refactoring": "claude-sonnet-5",
      "bugfix": "claude-sonnet-5",
      "feature": "claude-sonnet-5",
      "tests": "claude-sonnet-5",
      "docs": "claude-haiku-4-5"
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
