# Project Context — ai-orch (orquestador v1)

**Last updated**: 2026-06-21
**Updated by**: Claude Code

---

## What works right now

- `ai-orch init` — Creates `AGENTS.md` at the project root + `.ai/` folder with 6 template files
- `ai-orch triage` — Parses alerts, checks secrets, merge conflicts, runs tests
- `ai-orch check` — Pre-commit guard: blocks commit if code changed but neither `AGENTS.md` nor `.ai/` was updated
- `ai-orch hook-install` — Installs git pre-commit hook
- `ai-orch handoff` — Interactive wizard: updates `.ai/` docs and optionally commits

All 16 tests pass. No active alerts.

---

## Most recently changed

- `src/aiorch/main.py` — `init` now writes `AGENTS.md` to the project root instead of `.ai/ORCHESTRATOR.md` (skipped with a warning if one already exists); `check` now treats edits to root `AGENTS.md` as a valid context update (DEC-005)
- `src/aiorch/templates/ORCHESTRATOR.md` — removed; replaced by `src/aiorch/templates/AGENTS.md`
- `.ai/ORCHESTRATOR.md` (this project's own instance) — removed; replaced by root `AGENTS.md`
- `tests/test_cli.py` — added tests for AGENTS.md placement, no-overwrite behavior, and `check` accepting AGENTS.md updates (16 tests total)
- `README.md`, `CLAUDE.md` — updated to describe the AGENTS.md-based architecture

---

## Key numbers

| Metric | Value |
|--------|-------|
| Python version | 3.10+ |
| Commands | 5 (init, triage, check, hook-install, handoff) |
| Tests | 16 (all passing) |
| Dependencies | typer>=0.9.0, rich>=13.0.0 |
| Entry point | `ai-orch` |
| Template files | 7 (1 → project root as `AGENTS.md`, 6 → `.ai/`) |

---

## Stack

- Language: Python 3.11
- CLI framework: Typer 0.26.7
- Terminal UI: Rich 13.x
- Agent orchestration: Ruflo (claude-flow) MCP
- Skills system: Superpowers 5.1.0
- Tests: pytest

---

## Next steps (Block 2)

- Add README.md (done in this session)
- Complete pyproject.toml metadata for PyPI
- Add error path tests (invalid inputs, missing `.ai/` folder)
- Consider `ai-orch status` dashboard command
- Ruflo memory integration: auto-store session context at handoff
