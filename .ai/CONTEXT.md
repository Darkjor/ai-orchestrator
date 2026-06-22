# Project Context — ai-orch (orquestador v1)

**Last updated**: 2026-06-22
**Updated by**: Claude Code

---

## What works right now

- `ai-orch init` — Creates `AGENTS.md` at the project root + `.ai/` folder with 6 template files, auto-detecting the host project's name/stack/type/run+test commands and writing them into `.ai/config.json`
- `ai-orch triage` — Parses alerts, checks secrets, merge conflicts, runs tests
- `ai-orch check` — Pre-commit guard: blocks commit if code changed but neither `AGENTS.md` nor `.ai/` was updated
- `ai-orch hook-install` — Installs git pre-commit hook
- `ai-orch handoff` — Interactive wizard: updates `.ai/` docs and optionally commits

All 19 tests pass. No active alerts.

---

## Most recently changed

- `src/aiorch/main.py` — added `detect_project_context()`: reads `pyproject.toml`/`package.json`/`go.mod`/`Cargo.toml` (falls back to directory name) and merges the result into `.ai/config.json` on `init`; `init` also stamps today's date into `.ai/CONTEXT.md`'s "Current State" header; when no stack is detected, `init` now warns the user to fill in `.ai/config.json` by hand
- `tests/test_cli.py` — added `test_init_detects_python_project`, `test_init_detects_node_project`, `test_init_falls_back_to_directory_name` (asserts the new warning) (19 tests total)
- `README.md`, `CLAUDE.md` — documented the auto-detection behavior

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
