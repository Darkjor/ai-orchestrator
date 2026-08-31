---
name: arrival
description: Run the ai-orch arrival protocol at the start of a session — read the .ai/ context folder, triage open P0/P1/P2 alerts and pending manual actions, check for merge conflicts and exposed secrets, and report where the last agent stopped before doing any work.
argument-hint: "[optional: what you are about to work on]"
allowed-tools: Bash(ai-orch triage:*), Bash(ai-orch export:*), Bash(ls:*), Bash(cat:*), Read, Glob, Grep
---

# Arrival protocol

You are arriving at a project that keeps its memory in `.ai/`. Read the situation
before touching anything. This costs a minute and prevents redoing a day of work.

$ARGUMENTS

## 1. Check the folder exists

```bash
ls .ai/
```

No `.ai/` folder → this project is not orchestrated. Say so, offer `ai-orch init`
(see the `ai-orch` skill), and stop. Do not fabricate the folder.

## 2. Triage

```bash
ai-orch triage
```

This prints open alerts, pending manual actions, the project's model routing, a merge
conflict scan, a secret-file scan, and runs `config.test_command`. If `ai-orch` is not
installed, read `.ai/ALERTS.md` and `.ai/PENDING.md` directly instead and say the CLI
is missing.

## 3. Read the state

```bash
cat .ai/CONTEXT.md
```

`## Current State` is where the previous agent said what works and what broke.
`## Most recently changed` is the file list from the last session only. If you need
everything (deep analysis, or you are about to make an architectural call), run
`ai-orch export` for the full bundle rather than reading files one at a time.

Then read `.ai/WHEELS.md` — approaches already tried and rejected. Do not re-litigate
a `FAIL-XXX` entry without a reason the entry does not already answer.

## 4. Decide what to do

- **A P0 alert exists and touches what you were asked to do** → handle the P0 first,
  or state plainly why you cannot. Do not start the requested task around it.
- **Only P1/P2** → note them, proceed.
- **Pending actions blocking your task** (an unrun migration, an unprovisioned
  service) → say so before writing code that assumes they are done.
- **Otherwise** → proceed with the user's request.

## 5. Report back

Give the user a short brief before starting work:

- where the last session stopped
- open alerts by severity, and whether any block the current task
- pending manual actions that are in your way
- what you are going to do first

Keep it to a few lines. If the state is clean and nothing blocks the task, say that in
one sentence and get to work — the protocol is a check, not a ceremony.
