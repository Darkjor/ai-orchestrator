# Architecture Decisions — ai-orch (orquestador v1)

> Status values: Active | Superseded by DEC-XXX | Reversed

---

## [DEC-001] Typer over argparse/click for CLI framework

**Date**: 2026-06-01
**Status**: Active
**Context**: Needed a CLI framework for the 5 commands. Options: argparse (stdlib), click, typer.
**Decision**: Typer with type hints.
**Rationale**: Typer generates `--help` automatically from type hints, requires minimal boilerplate, and integrates naturally with Python 3.10+ type system. Rich integration is straightforward.
**Consequences**: Requires Python 3.10+. Slightly heavier than argparse but much better UX.
**Revisit when**: Python 3.9 support becomes needed.

---

## [DEC-002] Markdown files over database for `.ai/` context

**Date**: 2026-06-01
**Status**: Active
**Context**: AI agents need to read and write project context. Options: SQLite, JSON files, Markdown files.
**Decision**: Plain Markdown files (.ai/CONTEXT.md, ALERTS.md, etc.)
**Rationale**: Markdown is readable by any AI tool (Claude, Gemini, GPT) without tool calls. Human-readable in any editor. Works with git diff. No schema migrations.
**Consequences**: Parsing is fragile (regex-based). Cannot query across projects. Append-only updates can cause duplication.
**Revisit when**: Cross-project queries or structured queries become needed.

---

## [DEC-003] Pre-commit hook enforces .ai/ update on code changes

**Date**: 2026-06-01
**Status**: Active
**Context**: Agents frequently update code without updating the `.ai/CONTEXT.md`, causing context drift.
**Decision**: Block git commits if code files were staged but `.ai/` was not touched.
**Rationale**: Hard enforcement at commit time is the only reliable mechanism. Soft reminders get ignored.
**Consequences**: Adds friction to commits. Mitigated by `ai-orch handoff` which handles the update interactively.
**Revisit when**: A better context-sync mechanism exists (e.g., LSP hook, IDE plugin).

---

## [DEC-004] Merge conflict detection uses line-start regex

**Date**: 2026-06-05
**Status**: Active
**Context**: Original implementation used `"<<<<<<<" in content` which matched the string literal inside main.py itself, causing false positives.
**Decision**: Use `re.search(r'^<{7}', content, re.MULTILINE)` to require conflict markers at line start.
**Rationale**: Git conflict markers always appear at column 0. String literals containing `<<<<<<<` (as in this codebase) will not match.
**Consequences**: None — stricter match is correct behavior.
**Revisit when**: Never — this is the correct pattern.

---

## [DEC-005] Adopt AGENTS.md instead of a proprietary ORCHESTRATOR.md

**Date**: 2026-06-21
**Status**: Active
**Context**: `ORCHESTRATOR.md` duplicated the job of AGENTS.md, an open format originated by OpenAI (Aug 2025) for Codex CLI and now governed by the Linux Foundation's Agentic AI Foundation, already adopted by 25+ tools (Codex, Cursor, GitHub Copilot, Windsurf, Claude Code). A bespoke arrival-protocol file is invisible to any agent that doesn't already know this project's specific convention — defeating the goal of cross-agent compatibility this project exists for.
**Decision**: `ai-orch init` now writes `AGENTS.md` to the project root (skipped with a warning if one already exists) instead of `.ai/ORCHESTRATOR.md`. `.ai/` keeps only what AGENTS.md and ADR tooling (adr-tools, MADR) don't already cover: `ALERTS.md` (severity-tagged triage), `DECISIONS.md`, `WHEELS.md`, `DISCUSSIONS.md`, `CONTEXT.md`, `config.json`. `check` now treats edits to root `AGENTS.md` the same as edits to `.ai/`.
**Rationale**: Conform to the standard agents already look for by default rather than competing with it. The project's genuine value is the enforcement mechanism (`check` + pre-commit hook) and the P0/P1/P2 alert/wheels system — not the instruction-file format.
**Consequences**: Breaks compatibility with any prior install that has `.ai/ORCHESTRATOR.md` (acceptable — project is alpha, no known external users). `init`'s file-distribution logic is no longer a flat copy loop; it special-cases one filename.
**Revisit when**: AGENTS.md stops being the dominant convention, or a successor standard emerges.
