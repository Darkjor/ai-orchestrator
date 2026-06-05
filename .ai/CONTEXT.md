# Project Context — ai-orch (orquestador v1)

**Last updated**: 2026-06-05
**Updated by**: Claude Code

---

## What works right now

- `ai-orch init` — Creates `.ai/` folder with 7 template files
- `ai-orch triage` — Parses alerts, checks secrets, merge conflicts, runs tests
- `ai-orch check` — Pre-commit guard: blocks commit if code changed but `.ai/CONTEXT.md` was not updated
- `ai-orch hook-install` — Installs git pre-commit hook
- `ai-orch handoff` — Interactive wizard: updates `.ai/` docs and optionally commits

All 10 tests pass. No active alerts.

---

## Most recently changed

- `src/aiorch/main.py` — Fixed false-positive merge conflict detection (line 139, regex `^<{7}`)
- `.ai/ALERTS.md` — Cleared template placeholder alerts, added resolved ALERT-001
- `.ai/config.json` — Configured for ai-orch project (model recommendations, test command)
- `.ai/ORCHESTRATOR.md` — Added Integrated Stack Protocol section (ai-orch + Ruflo + Superpowers)

---

## Key numbers

| Metric | Value |
|--------|-------|
| Python version | 3.10+ |
| Commands | 5 (init, triage, check, hook-install, handoff) |
| Tests | 10 (all passing) |
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
