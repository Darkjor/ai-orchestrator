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
