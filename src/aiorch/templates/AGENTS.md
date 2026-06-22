# AGENTS.md

Read these files before making any change, in this order:

1. `.ai/CONTEXT.md` — current state: what works, what's broken, what changed last
2. `.ai/ALERTS.md` — open P0/P1/P2 issues. A P0 blocks all new feature work
3. `.ai/WHEELS.md` — approaches already tried and rejected here; don't repeat them

## Commands

Run and test commands are defined in `.ai/config.json` (`run_command`, `test_command`).

## Boundaries

**Always:**
- Update `.ai/CONTEXT.md` after any change that affects project state
- Run the test command before considering work done

**Ask first:**
- Architectural changes — log the decision in `.ai/DECISIONS.md` before implementing
- Resolving or downgrading a P0/P1 alert in `.ai/ALERTS.md`

**Never:**
- Commit code changes without updating `.ai/` — enforced by the `ai-orch check` pre-commit hook
- Repeat an approach already logged as failed in `.ai/WHEELS.md`

## Session handoff

Before ending a session, run `ai-orch handoff` — it updates `.ai/CONTEXT.md`, `.ai/ALERTS.md`, `.ai/DECISIONS.md`, and optionally commits.

## Model routing (Claude-specific, optional)

Per-task-type model recommendations are in `.ai/config.json` → `models`.
