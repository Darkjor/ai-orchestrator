# Agent instructions — ai-orchestrator

Cross-tool entry point, read automatically by Antigravity (1.20.5+), Cursor and
Copilot. Claude Code reads `CLAUDE.md` instead.

**The full rules live in [CLAUDE.md](CLAUDE.md) — read it first, then
[docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) for the module map and data
contracts.** This file deliberately does not restate them: two copies of the
same rules is the exact drift problem this project exists to prevent.

## What this repository is

`ai-orch` — a CLI that keeps AI agents in sync across sessions by maintaining a
`.ai/` folder of Markdown context files, plus git hooks that block commits which
leave that context stale. Pure Python, no build step.

## Before you change anything

```bash
pip install -e ".[dev]"
pytest                    # 135 tests — the suite is the contract, keep it green
```

## The rules that break things most often

- `src/aiorch/main.py` is presentation only and must stay under 500 lines. Logic
  goes in a domain module; Rich rendering goes in `render.py` or `handoff_ui.py`.
- Every dict crossing a module boundary is declared as a TypedDict in
  `src/aiorch/models.py` first.
- Every git subprocess lives in `src/aiorch/gitops.py`.
- `src/aiorch/_helpers.py` is a re-export shim with a frozen public API. Never
  add logic there; never remove a name from it.
- Keep the `[OK]` / `[WARN]` / `[ERROR]` output prefixes — agents and tests parse them.
- Never `except: pass`. Log swallowed errors via `aiorch.logs.get_local_logger()`.
- Never commit secrets or `.env` files. Never add a `Co-Authored-By` trailer.

## This repo does not run its own guard

`.ai/` is gitignored here (commit `5e9f796`), so a `.ai/` path cannot be staged
and `ai-orch check` could never pass. **Do not run `ai-orch hook-install` in this
repository.** In projects that *use* ai-orch, the hooks are the whole point.

## Where the agent-facing assets live

| Path | For |
| --- | --- |
| `skills/` | Claude Code plugin skills (Agent Skills standard) |
| `hooks/hooks.json` | Claude Code SessionStart hook |
| `.claude-plugin/` | Plugin + marketplace manifests |
| `.agents/rules/` | Antigravity workspace rules |
| `src/aiorch/templates/` | What `ai-orch init` copies into a user's project |

The `skills/*/SKILL.md` files follow the Agent Skills open standard, so they work
unchanged if copied to `.agents/skills/` for Antigravity.
