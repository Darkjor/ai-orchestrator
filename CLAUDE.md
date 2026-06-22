# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Commands

```bash
# Install for local development
pip install -e .

# Run all tests
pytest

# Run a single test function
pytest tests/test_cli.py::test_init_creates_ai_folder

# Run the CLI directly after install
ai-orch --help
ai-orch init
ai-orch triage
ai-orch check
ai-orch hook-install
ai-orch handoff
```

There is no build step — this is a pure Python project with `setuptools`.

## Architecture

**Entry point**: `src/aiorch/main.py` — single file containing all CLI commands, registered as `ai-orch` via `pyproject.toml` `[project.scripts]`.

**CLI framework**: Typer (`app = typer.Typer()`). Each command is decorated with `@app.command()`. Output is rendered with Rich (`console = Console()`).

**Templates**: `src/aiorch/templates/` contains the 7 files `init` distributes. `AGENTS.md` goes to the project root (the open AGENTS.md standard agents already look for by default); the rest go into `.ai/`:

- `AGENTS.md` — agent instructions and boundaries; copied to the project root, not `.ai/`
- `CONTEXT.md` — current project state (updated by `handoff`)
- `ALERTS.md` — P0/P1/P2 issue tracker (parsed by `parse_alerts()`)
- `DECISIONS.md` — architecture decision log (appended by `handoff`)
- `DISCUSSIONS.md` — async agent threads
- `WHEELS.md` — failed approaches / do-not-reinvent list
- `config.json` — project metadata + Claude model recommendations per task type

**Command responsibilities**:

- `init` — copies `AGENTS.md` to the project root (skipped, with a warning, if one already exists) and the remaining templates into `.ai/`; is a no-op if `.ai/` already exists. Then runs `detect_project_context()` to auto-fill `.ai/config.json` (`project_name`, `project_type`, `project_stack`, `run_command`, `test_command`) from the host project's manifest files, and stamps today's date into `.ai/CONTEXT.md`'s "Current State" header
- `triage` — reads `.ai/ALERTS.md` via `parse_alerts()`, reads `.ai/config.json` for model recommendations, scans for merge conflicts, checks for secret files, optionally runs `test_command` from config
- `check` — git pre-commit guard; exits 1 if codebase files are staged but neither `.ai/` nor `AGENTS.md` was touched
- `hook-install` — writes `.git/hooks/pre-commit` that calls `ai-orch check`
- `handoff` — interactive wizard that updates `CONTEXT.md` (regex-replaces "Current State" date and injects bullets), appends to `ALERTS.md` and `DECISIONS.md`, and optionally `git add . && git commit`

**Project context detection**: `detect_project_context(root=".")` in `main.py` inspects the host project's manifest files to fill in real values instead of placeholders — `pyproject.toml` (regex for `[project] name` and `[project.scripts]` entries → Python/CLI), `package.json` (`name` + `scripts.start`/`scripts.test` → Node.js), `go.mod`, `Cargo.toml`, falling back to the directory name and `"Unknown"` stack when no manifest matches. Wrapped in try/except so a malformed manifest never breaks `init`.

**Tests**: `tests/test_cli.py` uses `typer.testing.CliRunner` with `tmp_path` fixtures. Tests `os.chdir()` into a temp directory and invoke commands directly through the runner. No mocking — tests call real git subprocess commands where needed.

**Model routing** (defined in `config.json` template):

- Architecture / code review → `claude-opus-4-8` (with extended thinking)
- Feature / bugfix / refactor / tests → `claude-sonnet-4-6`
- Docs → `claude-haiku-4-5-20251001`
