---
name: ai-orch
description: Use ai-orch to give a project persistent, cross-session memory for AI agents — a .ai/ folder of Markdown context files (CONTEXT, ALERTS, DECISIONS, PENDING, WHEELS) plus git hooks that block commits which leave that context stale. Load this when setting up shared context in a repo, when handing work between agents or sessions, when the user asks "where did we leave off", when context was lost or compacted, when recording a blocker/decision/manual DB or infra action, or when exporting project context to paste into another model.
when_to_use: Trigger phrases — "ai-orch", "orchestrator", "handoff", "hand off to another agent", "shared context", "session memory", "where did we leave off", "pick up where we stopped", ".ai folder", "context folder", "record a decision", "log a blocker", "pending migration", "export context for GPT/Gemini".
---

# ai-orch — cross-session memory for AI agents

`ai-orch` is a tech-agnostic Python CLI. It maintains a `.ai/` folder of Markdown
files that any agent (Claude, GPT, Gemini, Cursor, Copilot) reads on arrival and
updates on departure, and it installs git hooks that make staleness a commit error
rather than a habit.

**The one idea:** context lives in the repo, in Markdown, in git — not in a chat
transcript that dies with the session.

## Is it available?

```bash
ai-orch --help                    # installed?
ls .ai/ 2>/dev/null               # initialized in this project?
```

If the CLI is missing:

```bash
pip install "git+https://github.com/Darkjor/ai-orchestrator.git@master"
```

If `.ai/` is missing, see **Set up a new project** below. Never invent the folder by
hand — `ai-orch init` copies templates whose exact headings are parsing contracts.

## The `.ai/` folder

| File | Holds | Written by |
| --- | --- | --- |
| `ORCHESTRATOR.md` | The arrival protocol itself | `init` (then hand-edited) |
| `CONTEXT.md` | What works, what broke, what changed last | `handoff`, `update`, `snapshot` |
| `ALERTS.md` | P0/P1/P2 open issues | `handoff`, `qa` |
| `DECISIONS.md` | Append-only architecture decision log | `handoff` |
| `PENDING.md` | Manual actions no agent can do (SQL, infra, dashboards) | `action-add` / `action-resolve` |
| `WHEELS.md` | Failed approaches + machine-enforced `[LINT-XXX]` rules | hand-edited |
| `DISCUSSIONS.md` | Async threads between agents | hand-edited |
| `config.json` | Project metadata, `test_command`, model routing | hand-edited |
| `ANALYSIS.md` | Metrics report (runtime only) | `analyze` / `qa` |

## The daily loop

```
ARRIVE  →  ai-orch triage        (alerts, pending, conflicts, secrets, tests)
WORK    →  ai-orch update / action-add   (record as you go, not at the end)
LEAVE   →  ai-orch sync --note "..."     (agents)  |  ai-orch handoff (humans)
```

`/ai-orch:arrival` and `/ai-orch:handoff` run the two rituals. This skill is the
reference behind them.

## Commands

| Command | Use it when |
| --- | --- |
| `ai-orch init` | First time in a project — writes 8 template files into `.ai/` |
| `ai-orch triage` | Start of every session — the arrival brief |
| `ai-orch sync [--note "..."]` | End of a session — **the agent path**. Derives changed files from git, never prompts |
| `ai-orch handoff` | End of a session — **interactive**, prompts on stdin |
| `ai-orch update -s SECTION -v VALUE [-f FILE]` | Non-interactive replace of one specific section |
| `ai-orch brief [--out FILE]` | Render `.ai/` as one human-readable status page |
| `ai-orch ide-install` | Write `AGENTS.md` + `.agents/rules/` so other IDEs learn the protocol |
| `ai-orch action-add TITLE --type db\|infra\|other [--sql ...] [--steps ...]` | You found work only a human can do |
| `ai-orch action-resolve ID` | That work got done |
| `ai-orch snapshot [--src DIR]` | Refresh the AST symbol map in `CONTEXT.md` |
| `ai-orch analyze` → `ai-orch qa` | Write a metrics report, then verify it against live state |
| `ai-orch export [--out FILE]` | Bundle all `.ai/` files for a model that can't read the filesystem |
| `ai-orch check` | Pre-commit guard (the hook calls it; you rarely type it) |
| `ai-orch hook-install` | Install the pre-commit + post-commit hooks |
| `ai-orch observe [-n N]` | Recent run metrics, if Supabase is configured |

Every command prints `[OK]` / `[WARN]` / `[ERROR]` prefixes. Parse those, not prose.

## Writing context as an agent

**Use `sync` or `update`, never `handoff`, when running unattended.** `handoff` is
an interactive wizard: it blocks on `typer.prompt` and will hang a non-interactive run.

The one-command departure — git supplies the file list, you supply the reason:

```bash
ai-orch sync --note "Refactored auth; stopped at JWT refresh caching"
```

For writing one specific section by hand:

```bash
ai-orch update -s "Current State" -v "- Refactored auth\n- Stopped at JWT refresh caching"
ai-orch update -s "Most recently changed" -v "- src/auth.py: token validation"
ai-orch update -f ALERTS.md -s "P1" -v "- Redis connection pool leaks under load"
```

Rules that matter:

- `\n` in `--value` becomes a real newline. Pass multi-line content in one argument.
- Section matching is case-insensitive and prefix-based, so `"Current State"` matches
  `## Current State (updated: 2026-08-31)`.
- `update` **replaces** the whole section. Read the file first if you mean to append.
- Exit code 1 means the section heading was not found — check spelling before retrying.

## Set up a new project

```bash
cd your-project
ai-orch init            # creates .ai/ with 8 files
ai-orch hook-install    # pre-commit guard + post-commit snapshot
```

Then edit `.ai/config.json` — at minimum `project_name`, `stack`, and `test_command`
(triage runs it, with a 30s timeout).

**`.ai/` must be committed, not gitignored.** The guard requires a staged `.ai/` path
whenever code is staged; if `.ai/` is ignored, every code commit is blocked with no
way to satisfy it short of `--no-verify`. Check with `git check-ignore -v .ai/CONTEXT.md`
before installing hooks.

## The two automated loops

**Commit guard (pre-commit → `ai-orch check`).** Staged code with no staged `.ai/`
file → exit 1, commit blocked. `docs/`, `.gitignore` and `pyproject.toml` are exempt.
Then staged content is matched against `WHEELS.md` lint rules; a hit also blocks.
Broken or absent git → exit 0, never a harder block than git itself.

**Snapshot refresh (post-commit → `ai-orch snapshot --quiet`).** Re-derives the
`## Codebase Snapshot` section of `CONTEXT.md` from the AST of `src/`. Never blocks.

## Lint rules in WHEELS.md

Rules turn a documented lesson into an enforced one. They are parsed **only from
inside the `## 4. Lint Rules` section** — a rule appended anywhere else in the file is
silently ignored, with no warning.

```
### [LINT-001] No print debugging
**Pattern**: `print\(`
**Files**: *.py
**Message**: Use the logger, not print().
```

`Pattern` is a Python regex in backticks. `Files` are globs matched against the
**basename** only (`*.py`, not `src/**/*.py`); omit the field to match everything.
Rules are checked against the git **index** (`git show :path`), so an unstaged fix in
the working tree will not let a bad staged version through.

## analyze → qa (the anti-hallucination loop)

`analyze` collects only re-derivable numbers (pytest collection count, alert counts,
pending count, decision count, `git diff` file count) and writes `.ai/ANALYSIS.md` with
status `PENDING`. `qa` re-collects the live values and diffs them.

```
PENDING ──qa, metrics match──→ QA_APPROVED
        └─qa, mismatch───────→ QA_ESCALATED  (P1 alert + auto-heal action created)
                                    ├─ human answers y ─→ QA_APPROVED
                                    └─ human answers n ─→ HUMAN_REVIEWED (exit 1)
```

`qa` prompts for the override, so it also blocks unattended. Only P0 count and pending
count are cross-checked — test and git counts drift legitimately between the two runs.

## Other IDEs, and humans reading the repo

`ai-orch ide-install` writes an `AGENTS.md` (read automatically by Antigravity,
Cursor and Copilot) and an Antigravity workspace rule at
`.agents/rules/ai-orch.md` with `trigger: always_on`, so an agent in those tools
learns the protocol with no plugin installed. Both are written as a managed block
between `<!-- ai-orch:start -->` markers — regenerating never touches text a human
wrote around it.

`ai-orch brief` renders the live `.ai/` state as one page written for a person:
what is happening, what is broken, what needs a human, where the detail lives.
Point it somewhere discoverable (`--out STATUS.md`) for teammates who browse the
repo in an IDE and will never run the CLI.

## Handing off to a non-Claude model

```bash
ai-orch export --out context.md     # or: ai-orch export | pbcopy
```

Produces one Markdown document (ORCHESTRATOR, CONTEXT, ALERTS, DECISIONS, PENDING,
WHEELS, DISCUSSIONS in arrival-reading order) to paste as a first message.

## Gotchas

- `handoff` and `qa` block on stdin. In automation use `update` / `action-add`, and
  check `analyze` output rather than running `qa`.
- Alert and action IDs are **never reused** — resolved entries still reserve their
  number, so cross-references in old commits stay valid.
- Severity and type are **positional**: an alert's severity is whichever `## P0` /
  `## P1` / `## P2` section it sits under. Moving a block changes its meaning.
- `triage` runs `config.test_command` through a shell. Treat that field with the same
  trust you would a Makefile.
- Errors that get swallowed are logged to `.ai/logs/aiorch.log` — read it when a
  command silently does less than you expected.
- Never bypass the guard with `git commit --no-verify`. Update `.ai/` instead; that is
  the entire point of the tool.

## Extending it

Full module map and data contracts: `docs/AI_ARCHITECTURE.md` in the ai-orchestrator
repo. Short version — `main.py` is presentation only, logic lives in one domain module
per concern, every dict crossing a module boundary is a TypedDict in `models.py`, all
git subprocesses live in `gitops.py`, and the test suite is the contract.
