---
name: handoff
description: Close an ai-orch session cleanly — write what you did and where you stopped into .ai/CONTEXT.md, log new blockers as alerts, record architecture decisions, file manual DB/infra actions in PENDING.md, and commit so the next agent (or the next you, after a compaction) can resume without re-deriving anything.
argument-hint: "[optional: summary of what you did]"
allowed-tools: Bash(ai-orch update:*), Bash(ai-orch action-add:*), Bash(ai-orch action-resolve:*), Bash(ai-orch snapshot:*), Bash(ai-orch triage:*), Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Read, Glob, Grep
---

# Session handoff

Write down what the next agent would otherwise have to rediscover. Run this before
ending a session, before a context compaction, and any time you are about to run out
of room mid-task.

$ARGUMENTS

**Use `ai-orch update`, not `ai-orch handoff`.** The `handoff` command is an
interactive wizard that blocks on stdin prompts — it will hang you. `update` is the
non-interactive writer built for agents.

## 1. Gather what actually changed

```bash
git status --short
git diff --stat
```

Base the handoff on the real diff, not on your memory of the conversation.

## 2. Write the state

```bash
ai-orch update -s "Current State" -v "- <what works now>\n- <what is broken>\n- <exactly where you stopped>"
ai-orch update -s "Most recently changed" -v "- path/to/file.py: <what changed and why>"
```

`update` **replaces** the section. Read `.ai/CONTEXT.md` first if you mean to keep what
is there. `\n` in the value becomes a real newline. Exit code 1 means the heading was
not found — check the file for the exact spelling.

If you stopped mid-task, the single most valuable line you can write is the precise
stopping point: the function, the failing assertion, the decision you had not made yet.

## 3. Log what you found

New blocker discovered:

```bash
ai-orch update -f ALERTS.md -s "P1" -v "- <symptom, impact, and what you already ruled out>"
```

Severity is positional — the section you write into *is* the severity. P0 is "nobody
can work until this is fixed".

Work only a human can do (cloud console, credential rotation, a migration on a live
database):

```bash
ai-orch action-add "Add index on orders.customer_id" --type db --sql "CREATE INDEX ..."
ai-orch action-add "Rotate the staging API key" --type infra --target "Vault"
```

A manual action you completed this session:

```bash
ai-orch action-resolve DB-001
```

Architecture decision you made: append it to `.ai/DECISIONS.md` — the log is
append-only, so add a new entry that supersedes the old one rather than editing it.
Record the context and the rationale, not just the verdict.

Approach you tried that did not work: add a `FAIL-XXX` entry to `.ai/WHEELS.md` with
the root cause and what you did instead. This is what stops the next agent from
spending the same hour. If the failure is a pattern that should be *enforced* rather
than remembered, add a `[LINT-XXX]` rule inside the `## 4. Lint Rules` section — rules
written anywhere else in the file are silently ignored.

## 4. Refresh the symbol map

```bash
ai-orch snapshot
```

Only if you added or removed top-level functions or classes. The post-commit hook does
this automatically when hooks are installed.

## 5. Commit

```bash
git add -A
git commit -m "<type>: <what changed>"
```

The pre-commit hook runs `ai-orch check`: staged code with no staged `.ai/` file fails
the commit, and so does a `WHEELS.md` lint violation. If it blocks you, the fix is to
write the context you skipped — **never** `--no-verify`.

Only commit if the user asked you to, or if committing is the established rhythm of
the session.

## 6. Confirm

Tell the user in a few lines what you recorded, what you left open, and what the next
session should pick up first.
