# Triage Protocol — Universal Health Check

> Run this in your FIRST 5 MINUTES in any project.
> Do NOT skip it. Stale context + unchecked fires = wasted work.
> This file is generic — it works for any project type.

---

## Step 1 — Run the Checks

Answer YES or NO to each. Mark the ones that apply.

### P0 — Critical (if any YES → stop, fix this before anything else)

- [ ] **Project can't run** — main entry point fails, build broken, or critical crash on start
- [ ] **Unresolved merge conflicts** — files contain `<<<<<<` markers
- [ ] **Tests that were passing are now failing** — regression introduced
- [ ] **Active production outage** — real users are affected right now
- [ ] **Security credential exposed** — .env or secret committed, needs immediate rotation

### P1 — Important (fix this session if it relates to your work)

- [ ] **Known bug blocking a user-facing flow** — not a crash, but something is broken
- [ ] **ALERTS.md has a P0 with no owner** — someone needs to claim it
- [ ] **CONTEXT.md hasn't been updated in 3+ days** — context is stale
- [ ] **A task is marked In Progress with no recent commit** — might be abandoned

### P2 — Normal (note it, address in planned work)

- [ ] CHANGELOG.md missing recent entries
- [ ] PROGRESS.md / AI_TASKS.md not reflecting current state
- [ ] Code file approaching 500 lines (split in next session)
- [ ] A TODO comment older than 2 weeks

---

## Step 2 — Make the Decision

```
P0 found?
  YES → Go to ALERTS.md. Do NOT start feature work until P0 is resolved or handed off.
  NO  → Continue.

P1 found?
  YES → Evaluate: does it block YOUR planned task? Fix first if yes.
  NO  → Continue.

Nothing critical?
  → Read AI_TASKS.md, claim a task, start working.
```

---

## Step 3 — Log What You Found

After running triage, add a one-liner to `.ai/CONTEXT.md` under "Most recently changed":

```
[YourAI] [date] — Triage: P0=0, P1=2, P2=1. Proceeding with TASK-XXX.
```

If you found something new, add it to `.ai/ALERTS.md`.

---

## Urgency Reference

| Level | Meaning | Action |
|-------|---------|--------|
| P0 | Everything stops | Fix or escalate immediately. Block new features. |
| P1 | Important friction | Fix if it affects your session. Leave a note if not. |
| P2 | Technical debt | Acknowledge. Add to AI_TASKS.md if not there. |
| RESOLVED | Fixed | Keep in ALERTS.md with resolution date for history. |

---

*This file is universal. Do not put project-specific content here.*
*Project-specific fires go in `.ai/ALERTS.md`.*
