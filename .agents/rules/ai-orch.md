---
trigger: always_on
description: >-
  Entry point for the ai-orchestrator repository. Points the agent at AGENTS.md
  and CLAUDE.md for the full contribution rules, the 500-line cap on main.py,
  the TypedDict and gitops boundaries, and the frozen _helpers public API.
  Applies to every task in this workspace.
---

Read `AGENTS.md` at the repository root before your first edit, then
`CLAUDE.md` and `docs/AI_ARCHITECTURE.md`.

Those files are the single source of truth for this repo's rules — this rule
only guarantees you are pointed at them on every task. Do not restate or
summarise them here; keeping one copy is the point.

Fast checks before any commit: `pip install -e ".[dev]" && pytest`.
