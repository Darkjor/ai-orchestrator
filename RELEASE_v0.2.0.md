# ai-orch v0.2.0

Production-ready release of the AI Orchestrator CLI — a global, tech-agnostic
framework for keeping AI coding agents aligned on shared project context.

## Highlights

This release graduates `ai-orch` from an alpha prototype to a production-ready
CLI, adding four new commands, a documentation suite, and substantial
performance work. There are **no breaking changes** — upgrading from 0.1.0
requires no migration.

## New Features

- **`action-add`** — record a pending action item to `.ai/PENDING.md` without
  running the full handoff wizard.
- **`action-resolve`** — mark a pending action as resolved and clear it from
  `.ai/PENDING.md`.
- **`snapshot`** — capture a point-in-time snapshot of the current `.ai/`
  context state.
- **`update`** — non-interactive replacement of a named section in a context
  file (scriptable alternative to the `handoff` wizard).

## Architecture Improvements

- Refactored the `handoff` flow and extracted shared logic into
  `src/aiorch/_helpers.py` for reuse across commands.
- Improved error handling at filesystem and git boundaries with clearer
  user-facing messages.
- A new `PENDING.md` template ships with `init` to back the action commands.

## Performance

- **Regex caching** — compiled patterns are cached, cutting repeated parse
  overhead by roughly 80%.
- **`git grep` conflict detection** — merge-conflict scanning now uses
  `git grep` instead of a full-tree Python walk.
- **`config.json` caching** — model-routing config is read once and reused
  within a command invocation.

## Testing

- Added 21 new tests covering the new commands and edge cases.
- **53 tests total, all passing** (`pytest tests/ -v`).

## Documentation

- Expanded `README.md` with the new commands and workflows.
- New `docs/API.md` — command and helper API reference.
- New `docs/TROUBLESHOOTING.md` — common issues and fixes.
- New `docs/MULTI_AGENT_FAQ.md` — multi-agent coordination guidance.

## Migration Notes

No breaking changes. Existing `.ai/` folders continue to work unchanged; run
`ai-orch init` in a fresh project to pick up the new `PENDING.md` template.

## Install

```bash
pip install ai-orchestrator
ai-orch --help
```
