# AI Orchestrator v2 — CEO Mode

> You are arriving at this project as an intelligent agent.
> Do not jump into tasks. Do not start coding. Run the arrival protocol first.
> This takes 5 minutes and saves hours of misdirected work.

---

## ARRIVAL PROTOCOL — All AIs, Always, No Exceptions

### Minute 1 — Read the situation
1. Read `.ai/CONTEXT.md` — what works, what's broken, what changed last (60 sec)
2. Read `.ai/ALERTS.md` — what's on fire right now
3. Read `.ai/WHEELS.md` — things we do NOT reinvent, stack, and failed experiments

### Minute 2 — Triage decision

```
P0 alert exists AND affects your capability?
  → Go to ALERTS.md. Fix the P0 or document why you can't.
  → Do NOT touch any other task until P0 is handled.

Only P1/P2 alerts?
  → Note them. Proceed to step 3.

No alerts?
  → Proceed to step 3.
```

### Minute 3 — Check Discussions
1. Read `.ai/DISCUSSIONS.md` — review recent handoff threads and open questions.
2. If another agent left a question or handoff for you, review it, reply/validate their code, and resolve if appropriate.

### Before You Leave (mandatory)

Before ending your session, update:

| File | What to update |
|------|---------------|
| `.ai/CONTEXT.md` | Current State + Most Recently Changed |
| `.ai/ALERTS.md` | New fires discovered, resolved alerts |
| `.ai/DISCUSSIONS.md` | Handoff thread or open debate with your progress / questions |
| `.ai/DECISIONS.md` | Any architectural decision you made |

**If you run out of tokens mid-task**: update CONTEXT.md with exactly where you stopped.
The next AI will pick up from there.

---

## Model Selection Guide

The recommended Claude model depends on task complexity and budget:

| Task Type | Recommended Model | When to Use | Benefits |
|-----------|------------------|-------------|----------|
| **Architecture** | claude-opus-4-8 | System design, major refactors, complex decisions | Extended thinking mode (reasoning) |
| **Code Review** | claude-opus-4-8 | Peer review, security audit, performance analysis | Extended thinking for thorough analysis |
| **Refactoring** | claude-sonnet-4-6 | Code cleanup, pattern improvements, modernization | Best balance of capability and cost |
| **Bugfix** | claude-sonnet-4-6 | Fixing bugs, debugging issues | Sufficient for targeted fixes |
| **Feature** | claude-sonnet-4-6 | New functionality, feature development | Good cost/capability ratio |
| **Tests** | claude-sonnet-4-6 | Test writing, test maintenance | Capable for test generation |
| **Documentation** | claude-haiku-4-5 | Docs, comments, content writing | Lightweight, cost-effective |

**Extended Thinking Mode**: Recommended for architecture and code review tasks. Use this when problem-solving requires deep analysis.

**Default**: This project uses `claude-sonnet-4-6` by default, with Opus reserved for critical decisions.

Check `.ai/config.json` for this project's specific model recommendations.

---

## Project Quick-Read

```
PROJECT: <project_name>
TYPE:    <project_type>
STATUS:  <project_status>
STACK:   <project_stack>
RUN IT:  <command_to_run_project>
TASKS:   <where_tasks_are_tracked>
```
