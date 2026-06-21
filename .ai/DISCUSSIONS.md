# Agent Discussions & Handoff Board

> Use this file to discuss architecture, resolve doubts, and hand over tasks.
> Before starting a task: check active threads with status `[Open]` or `[Awaiting Review]`.
> Resolve threads by marking them as `[Resolved]` and writing a summary of the decision.

---

## [THREAD-001] Project Bootstrap & Initial Handoff

- **Status**: `[Resolved]`
- **Created**: 2026-06-05 by Antigravity
- **Context**: The repository is being initialized with the AI Orchestrator v2 framework.
- **Replies**:
  - *Developer*: Project approved. Ready to test.

---

## [THREAD-002] Block 1 Integration Complete — Stack ai-orch + Ruflo + Superpowers

- **Status**: `[Resolved]`
- **Created**: 2026-06-05 by Claude Code (Hat: ORCHESTRATOR)
- **Context**: Completed full integration of ai-orch CLI with Ruflo MCP and Superpowers skills.
- **Summary of work:**
  - ai-orch initialized on its own project (dogfooding)
  - Ruflo MCP initialized — 17 agents, 30 skills, hooks active, memory DBs live
  - Bug fix: merge conflict regex → line-start match (DEC-004)
  - WHEELS.md filled with actual project content (stack, patterns, WHEEL-001)
  - ORCHESTRATOR.md: replaced routing section with 6-Hat system
  - ORCHESTRATOR.md: replaced compatibility table with actionable per-AI instructions
  - .gitignore: added `.claude/` to protect private hooks
  - tests/test_cli.py: removed test_placeholder, added 5 error-path tests (14 total)
  - All 14 tests passing, triage fully clean
- **Next session:** Start with Hat: ORCHESTRATOR → triage → pick Block 2 task from CONTEXT.md

---

## [THREAD-003] Pivot: AGENTS.md adoption (replacing ORCHESTRATOR.md)

- **Status**: `[Resolved]`
- **Created**: 2026-06-21 by Claude Code
- **Context**: While comparing ai-orch against Graphify, identified that `ORCHESTRATOR.md` reinvented AGENTS.md, an open standard now backed by the Linux Foundation and adopted by 25+ AI coding tools. Decided to pivot rather than let the project stagnate on a redundant format (see DEC-005, WHEELS.md FAIL-002).
- **Summary of work:**
  - `src/aiorch/templates/ORCHESTRATOR.md` removed, replaced by `src/aiorch/templates/AGENTS.md`
  - `init` now writes `AGENTS.md` to the project root (skips with a warning if one already exists there)
  - `check` now accepts edits to root `AGENTS.md` as a valid context update, same as `.ai/`
  - Tests: added coverage for AGENTS.md placement, no-overwrite behavior, and the updated `check` guard (14 → 16 tests, all passing)
  - This project's own `.ai/ORCHESTRATOR.md` retired; this project now has its own root `AGENTS.md` (dogfooding)
  - README.md, CLAUDE.md updated to describe the new architecture
- **Next session:** Verify there are no remaining references to `.ai/ORCHESTRATOR.md` outside this thread's history; consider whether `.ai/TRIAGE.md` (present in this project but not in `templates/`) should become an 8th template or be folded into `AGENTS.md`.
