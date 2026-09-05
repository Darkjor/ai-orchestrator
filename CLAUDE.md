# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) — and any other AI agent —
when working with code in this repository. For the full module map and data contracts,
read [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) first.

## Session Memory

This repo no longer self-hosts its own `.ai/` folder (removed 2026-08-07). When nested
inside another project's workspace, its context lives consolidated in that project's own
`.ai/` folder — e.g. `../.ai/AI-ORCHESTRATOR.md` when nested under a host project, per the
author's decision that a workspace should have a single `.ai/` folder rather than one per
nested repo. If running this repo standalone (not nested), there is currently no `.ai/`
context to auto-load — read `docs/AI_ARCHITECTURE.md` and recent git history instead.

**Decisions index** (full context/rationale/consequences behind each of these now lives in
git history — `git log --all --oneline -- .ai/DECISIONS.md` — and in a condensed form in the
host workspace's `.ai/AI-ORCHESTRATOR.md` when nested):

- DEC-001 — Typer over argparse/click for the CLI framework
- DEC-002 — Markdown files over a database for `.ai/` context
- DEC-003 — Pre-commit hook enforces `.ai/` update on code changes
- DEC-004 — Merge conflict detection uses line-start regex, not substring match
- DEC-005 — Architecture review: scalability bottlenecks & technical debt (findings only)
- DEC-006 — v0.3.0 domain-module split for agentic maintainability
- DEC-007 — CLAUDE.md imports the arrival protocol instead of relying on manual Read
- DEC-008 — `.ai/DECISIONS.md` itself is indexed here, not imported in full (this section)

## Rules

- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary — prefer editing existing files
- NEVER create documentation files unless explicitly requested
- NEVER save working files or tests to root — use `/src`, `/tests`, `/docs`, `/config`, `/scripts`
- ALWAYS read a file before editing it
- NEVER commit secrets, credentials, or .env files
- NEVER add a `Co-Authored-By` trailer to commits
- Keep files under 500 lines
- Validate input at system boundaries
- Declare any dict that crosses a module boundary as a TypedDict in `src/aiorch/models.py`
- Log swallowed errors via `aiorch.logs.get_local_logger()` — never `except: pass` silently
- Keep the `[OK]` / `[WARN]` / `[ERROR]` output prefixes — agents and tests parse them
- Never add logic to `src/aiorch/_helpers.py` — it is a re-export shim only
- Agents exchange `ai-orch/v1` JSON envelopes, never prose — validate each handoff
  with `ai-orch validate`; see [skills/pipeline/SKILL.md](skills/pipeline/SKILL.md)
- Role prompts in `.ai/config.json` are versioned code: bump `version`, add a
  `prompt_changelog` line, and evaluate against real cases before replacing one
- Do not add "think step by step", assistant prefills, `budget_tokens`, or sampling
  params to prompts — the last three are hard 400s on current models

## Commands

```bash
# Install for local development
pip install -e .

# Run all tests / a single test
pytest
pytest tests/test_cli.py::test_init_creates_ai_folder

# CLI (all 19 commands)
ai-orch setup             # init + hook-install + ide-install in one (start here)
ai-orch init              # create .ai/ from templates (8 files)
ai-orch triage            # alerts + pending + model routing + conflict/secret scan + tests
ai-orch check             # pre-commit guard: code staged without .ai/ update → exit 1
ai-orch hook-install      # writes .git/hooks/pre-commit and post-commit
ai-orch handoff           # interactive session-handoff wizard (--snapshot to embed symbols)
ai-orch sync              # non-interactive handoff for agents: --note WHY, git supplies WHAT
ai-orch snapshot          # AST symbol snapshot → CONTEXT.md (--src DIR, --quiet)
ai-orch update            # non-interactive section replace: -s SECTION -v VALUE [-f FILE]
ai-orch action-add        # add manual action to PENDING.md (--type db|infra|other, --sql, --steps)
ai-orch action-resolve    # move a PENDING.md action to ## DONE by ID
ai-orch analyze           # write verifiable metrics report to .ai/ANALYSIS.md
ai-orch qa                # cross-check ANALYSIS.md vs live state; escalate on mismatch
ai-orch export            # bundle all .ai/ files to stdout or --out FILE
ai-orch brief             # render .ai/ as one human-readable status page (--out FILE)
ai-orch ide-install       # write AGENTS.md + CLAUDE.md @imports + .agents/rules/
ai-orch validate          # check a structured inter-agent envelope (--role to pin the sender)
ai-orch roles             # list agent role prompts and their versions
ai-orch observe           # show Supabase run metrics (needs SUPABASE_URL/_ANON_KEY)
```

There is no build step — pure Python with `setuptools`.

## Architecture

**Entry point**: [src/aiorch/main.py](src/aiorch/main.py) — Typer app (`ai-orch` via
`[project.scripts]`). Presentation only: prompts, Rich rendering, exit codes. Must stay
under 500 lines — put logic in the domain modules.

**Domain modules** (single responsibility, all in `src/aiorch/`):

| Module | Owns |
| --- | --- |
| `models.py` | TypedDict contracts (`Alert`, `PendingAction`, `LintRule`, `ProjectMetrics`, ...) |
| `alerts.py` | ALERTS.md parsing/insertion; IDs never reused after resolution |
| `pending.py` | PENDING.md actions lifecycle (insert → resolve → ## DONE) |
| `context.py` | CONTEXT.md section editing, AST snapshot, export bundle |
| `decisions.py` | DECISIONS.md append-only decision log |
| `analysis.py` | analyze→qa anti-hallucination pipeline (status: PENDING→QA_APPROVED/ESCALATED) |
| `gitops.py` | every git subprocess + hook scripts; queries raise `GitCommandError` |
| `lint.py` | WHEELS.md `[LINT-XXX]` rules checked against the git index at pre-commit |
| `config.py` | forgiving `.ai/config.json` loader (corrupt → `{}` + warning) |
| `logs.py` | local logger: WARNING+ → stderr, DEBUG+ → `.ai/logs/aiorch.log` |
| `pipeline.py` | structured inter-agent envelope: schema, legal transitions, evidence rule |
| `portability.py` | AGENTS.md / CLAUDE.md imports / Antigravity rules + the brief (aggregator) |
| `analysis_ui.py` | analyze/qa presentation (takes `get_logger` from main — frozen patch point) |
| `render.py` | shared Rich rendering lifted out of `main.py` (triage helpers, runs table) |
| `observability.py` | optional Supabase `agent_runs` logger; never raises, off without env vars |
| `_helpers.py` | backward-compat re-export shim (frozen public API, incl. `_`-prefixed aliases) |

**Templates**: `src/aiorch/templates/` — 9 files; `init` copies 8 of them into `.ai/`
(`ANALYSIS.md` is runtime-only, generated by `analyze`).

**Cross-IDE assets**: `AGENTS.md` (this repo's rules for Antigravity/Cursor/Copilot —
it points at CLAUDE.md rather than restating it; keep one source of truth) and
`.agents/rules/ai-orch.md` (Antigravity `trigger: always_on`). `skills/` holds the
Claude Code plugin skills, which follow the Agent Skills standard and work unchanged
if copied to `.agents/skills/`.

**Tests**: `tests/` uses `typer.testing.CliRunner` with `tmp_path` + `os.chdir()`, real
git subprocesses, no filesystem mocking. The suite is the contract: keep it green, and
never break `aiorch.main.app`, `aiorch._helpers.*`, or `aiorch.main.get_logger`.

**Model routing** (template `config.json`, surfaced by `triage`/`handoff`):

- Architecture / code review → `claude-opus-5` (extended thinking)
- Feature / bugfix / refactor / tests → `claude-sonnet-5`
- Docs → `claude-haiku-4-5`

**Self-hosting note**: downstream projects install the hooks (`ai-orch hook-install`),
and there every commit that touches code must also update `.ai/` — run `ai-orch handoff`
or edit `.ai/CONTEXT.md`; never bypass it with `--no-verify`.

**Do not run `ai-orch hook-install` in THIS repo.** Since `.ai/` was gitignored
(commit `5e9f796`), a `.ai/` path can no longer be staged here, so `ai-orch check`
would block every code commit with no way to satisfy it. Either untrack the ignore for
this repo or leave the hooks uninstalled — the CI workflow does not run `check`.
