# Project Context — ai-orch (orquestador v1)

**Last updated**: 2026-06-05
**Updated by**: Claude Code

---

## What works right now

- `ai-orch init` — Creates `.ai/` folder with 7 template files
- `ai-orch triage` — Parses alerts, checks secrets, merge conflicts, runs tests
- `ai-orch check` — Pre-commit guard + WHEELS.md lint enforced on staged files
- `ai-orch hook-install` — Installs git pre-commit hook
- `ai-orch handoff` — Interactive wizard: updates `.ai/` docs and optionally commits

All 19 tests pass. No active alerts.

---

## Most recently changed

- `src/aiorch/main.py` — Added `ai-orch update` command (non-interactive section replacement)
- `src/aiorch/_helpers.py` — Added `update_section()` helper with prefix-matching for headings
- `tests/test_cli.py` — 4 new tests for update command (23 total)

---

## Key numbers

| Metric | Value |
|--------|-------|
| Python version | 3.10+ |
| Commands | 5 (init, triage, check, hook-install, handoff) |
| Tests | 19 (all passing) |
| Dependencies | typer>=0.9.0, rich>=13.0.0 |
| Entry point | `ai-orch` |
| Template files | 7 (in src/aiorch/templates/) |

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
