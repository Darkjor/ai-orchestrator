# Multi-Agent Workflow FAQ

Questions and answers for using `ai-orch` with multiple AI agents working on the same project.

---

## Coordination Basics

### Q: How do multiple agents avoid duplicating work?

**A:** Each agent reads the arrival protocol in `.ai/ORCHESTRATOR.md`:

1. **Read CONTEXT.md** — What's the current state? What changed last?
2. **Read ALERTS.md** — What's on fire? What needs fixing?
3. **Read DISCUSSIONS.md** — What are other agents working on?
4. **Read WHEELS.md** — What approaches already failed?

Before writing code, check `.ai/PENDING.md` for manual tasks (database migrations, infrastructure changes) that block development.

```bash
ai-orch triage  # Shows all active alerts and pending actions
cat .ai/ORCHESTRATOR.md  # Arrival protocol (mandatory read)
cat .ai/DISCUSSIONS.md   # See what other agents are doing
```

---

### Q: What happens if two agents work on the same file?

**A:** Git handles merges. However, `ai-orch` helps prevent conflicts:

1. **Update CONTEXT.md before starting:**
   ```bash
   ai-orch update --section "Most recently changed" --value "- src/auth.py (taken by Agent B)"
   git add .ai/CONTEXT.md && git commit -m "docs: claim auth.py"
   ```

2. **Use DISCUSSIONS.md to coordinate:**
   ```markdown
   ## Thread: Authentication Module Refactoring

   **Agent A (2024-01-15):**
   Starting refactor of src/auth.py. Will add async support.
   Estimated: 2 sessions. Testing with pytest.

   **Agent B (2024-01-16):**
   Agree! I'll wait for your PR then add OAuth integration on top.
   ```

3. **Handoff cleanly:**
   ```bash
   ai-orch handoff  # Updates CONTEXT.md and commits
   # Agent B can now safely start
   ```

---

### Q: How do I know what Agent X was doing?

**A:** Check `.ai/CONTEXT.md` and `.ai/DISCUSSIONS.md`.

**CONTEXT.md** shows:
- What changed last
- What broke recently
- Key architectural notes

**DISCUSSIONS.md** shows:
- Active threads between agents
- Questions from previous sessions
- Decisions that were debated

```bash
# Quick summary
head -30 .ai/CONTEXT.md
tail -50 .ai/DISCUSSIONS.md

# Or use ai-orch
ai-orch triage  # Shows model recommendations and pending tasks
```

---

### Q: Who owns a task? How do we assign work?

**A:** Use CONTEXT.md and DISCUSSIONS.md together:

**Document in CONTEXT.md:**
```markdown
## Current Owners

| Task | Owner | Status |
|------|-------|--------|
| API refactoring | Agent A | In Progress |
| Database optimization | Agent B | Blocked on P0 |
| Documentation | Pending | Not started |
```

**Track in DISCUSSIONS.md:**
```markdown
## API Refactoring (Owner: Agent A)

**Goal:** Convert to async/await pattern  
**Progress:** 40% (3 of 7 routes done)  
**Blocker:** JWT validation needs refactor first (P0)  
**Next steps:** Wait for Agent B to complete JWT work  

**Agent A** (2024-01-20): Ready to review PR when done.  
**Agent B** (2024-01-21): JWT refactor merged. You can start.
```

---

## Alert & Decision Management

### Q: How do agents prioritize work with alerts?

**A:** Severity determines priority (P0 > P1 > P2):

**P0 (Blocking):**
- Production outage, security breach, build broken
- Any agent who encounters it must stop and fix it
- Or document why they can't fix it

```bash
ai-orch triage | grep "P0"
# If any P0 exists, fix it first
```

**P1 (Important):**
- Major bugs, performance issues, missing features
- Plan for in the current or next session
- Can defer if blocked on external work

**P2 (Noted):**
- Minor bugs, tech debt, nice-to-haves
- Track but don't block other work
- Good for "spare time" tasks

---

### Q: How do we avoid conflicting architectural decisions?

**A:** Document decisions in `.ai/DECISIONS.md` before implementing:

**Process:**

1. **Agent A discovers a decision is needed:**
   ```bash
   ai-orch handoff
   # When asked "Do you want to document a new design decision?"
   # Answer: yes
   # Decision ID: DEC-005
   # Title: Use Redis for session caching
   # Context: Current in-memory sessions hit memory limits
   ```

2. **Decision is recorded in DECISIONS.md:**
   ```markdown
   ## [DEC-005] Use Redis for session caching
   **Date**: 2024-01-15
   **Status**: Active
   **Context**: In-memory session store uses too much memory
   **Decision**: Adopt Redis via Celery  
   **Rationale**: Redis is already in our stack; scales horizontally
   **Consequences**: +1 service to manage, +latency (sub-ms)
   **Revisit when**: Session volume exceeds 10k concurrent
   ```

3. **Agent B reads it before implementing:**
   ```bash
   cat .ai/DECISIONS.md | grep -A8 "DEC-005"
   # Now knows: use Redis, not Memcached or DynamoDB
   ```

4. **If Agent B disagrees:**
   ```markdown
   ## [DEC-005] Use Redis for session caching
   **Status**: Under Review  
   **Agent B's concern**: Redis RDB snapshots add 30s startup time.
   Consider Memcached + RocksDB instead?
   ```

---

### Q: How do we decide on new alerts vs. WHEELS.md entries?

**A:** Use this decision tree:

```
Does the issue block development right now?
├─ YES → Add to ALERTS.md with P0/P1/P2
│   └─ P0: "Cannot deploy" (add to BLOCKED section)
│   └─ P1: "Performance regressed" (important but not blocking)
│   └─ P2: "Minor UI bug" (can work around it)
│
└─ NO → Check if it's a failed approach
    └─ YES → Add to WHEELS.md under section "Failed Approaches"
    │   └─ Example: "FAIL-001: Python async with 3.8 timeouts badly"
    │
    └─ NO → Add to DISCUSSIONS.md as a question
        └─ Example: "Should we use FastAPI or Flask?"
```

---

## Handoff & Transitions

### Q: What should Agent A document before handing off?

**A:** Run this before you stop:

```bash
# 1. Update what changed
ai-orch update --section "Most recently changed" --value \
  "- src/auth.py: added JWT refresh\n- tests/test_auth.py: 8 new tests"

# 2. Update what works
ai-orch update --section "What works right now" --value \
  "- User login with email/password\n- JWT token generation"

# 3. Document blockers
ai-orch action-add "Redis cluster needs scaling" --type infra --target "AWS"

# 4. Add notes for next agent
ai-orch update --section "Next steps" --value \
  "- Implement 2FA (blocked on JWT work above)\n- Load test with 1000 concurrent users"

# 5. Commit everything
ai-orch handoff
```

**Output:**
- CONTEXT.md updated with current state + timestamp
- ALERTS.md appended with new issues
- DECISIONS.md appended with decisions made
- Git commit with session summary

---

### Q: How does Agent B pick up where Agent A left off?

**A:** Follow the arrival protocol (mandatory, ~5 minutes):

```bash
# 1. Triage the project
ai-orch triage
# Prints: P0/P1/P2 alerts, model recommendations, pending actions

# 2. Read context
cat .ai/CONTEXT.md
# Understand what changed, what's broken, where A stopped

# 3. Check for blocking work
cat .ai/PENDING.md | grep -A5 "## Database"
# See if there are migrations blocking development

# 4. Review decisions
cat .ai/DECISIONS.md | tail -20
# Understand architecture choices made

# 5. Check discussions
cat .ai/DISCUSSIONS.md
# Read open threads / handoff notes

# 6. Update CONTEXT to show you've arrived
ai-orch update --section "Current Session" --value "Agent B arrived. Reading context..."
```

---

### Q: How long should a "session" be?

**A:** No fixed length. Use your best judgment:

| Duration | When to handoff | What to document |
|----------|-----------------|-----------------|
| 30 min   | Quick fix       | One-line summary in DISCUSSIONS.md |
| 2-3 hrs  | Major feature   | Full handoff: `ai-orch handoff` |
| Mid-task | Running out of tokens | EXACT stopping point in CONTEXT.md |
| Unclear  | Ask yourself: "Can next agent continue from here?" | If no: add more notes |

**Example minimal handoff:**
```bash
ai-orch update --section "Most recently changed" --value \
  "- src/payment.py: added Stripe integration (lines 45-120)"
ai-orch update --section "Next steps" --value "- Test with test keys in staging"
git add .ai/ && git commit -m "docs: quick update before next session"
```

---

## Pending Actions & Manual Tasks

### Q: What goes in PENDING.md? What's an "action"?

**A:** Actions are manual, human-performed tasks that block or enable development:

**Database actions (DB-XXX):**
```bash
ai-orch action-add "Create users table" \
  --type db \
  --target "Supabase SQL Editor" \
  --sql "CREATE TABLE users (id SERIAL, email VARCHAR UNIQUE);"
```

**Infrastructure actions (INFRA-XXX):**
```bash
ai-orch action-add "Scale Redis cluster from 2 to 4 nodes" \
  --type infra \
  --target "AWS ElastiCache" \
  --steps "1. Go to ElastiCache console\n2. Modify node count\n3. Wait 10min"
```

**Other actions (ACTION-XXX):**
```bash
ai-orch action-add "Deploy to staging" \
  --type other \
  --target "GitHub Actions" \
  --steps "1. Merge to staging branch\n2. Approve deployment"
```

**DO NOT use for:**
- Code changes (those go in CONTEXT.md / ALERTS.md)
- Architecture decisions (those go in DECISIONS.md)
- Questions (those go in DISCUSSIONS.md)

---

### Q: How do we track who completed a manual action?

**A:** Use the "Owner" field in the action (if you extend PENDING.md):

Or document in DISCUSSIONS.md:

```markdown
## Manual Actions Completed

**INFRA-001**: Scale Redis cluster  
**Completed by**: DevOps Engineer (2024-01-21, 14:30 UTC)  
**Proof**: [Deployment link](https://aws.amazon.com/...)
```

Then mark as done:

```bash
ai-orch action-resolve INFRA-001
```

---

## Deduplication & Conflict Detection

### Q: How does ai-orch prevent duplicate alerts?

**A:** Alert IDs are unique and sequential:

```bash
# First alert in P0
ai-orch handoff → "ALERT-001"

# Next agent adds another P0
ai-orch handoff → "ALERT-002"

# Agents can check if alert already exists:
grep "ALERT-001" .ai/ALERTS.md
# If found, don't duplicate
```

**But:** Duplicate IDs can happen if agents work offline. Prevention:

```bash
# Always pull latest before adding alerts
git pull origin main

# Always commit after handoff
ai-orch handoff && git push origin main

# Check before adding (manual check)
ai-orch triage | grep "P0"
```

---

### Q: What if two agents add the same alert simultaneously?

**A:** Git merge conflict. Resolve manually:

1. **Pull and check:**
   ```bash
   git pull
   # Conflict in .ai/ALERTS.md
   ```

2. **Open the file:**
   ```bash
   nano .ai/ALERTS.md
   # Find merge markers: <<<<<<< HEAD ... ======= ... >>>>>>>
   ```

3. **Deduplicate:**
   ```markdown
   ## P0 — Blocking

   ### [ALERT-001] Production API timeout
   **Severity**: P0
   **Status**: Open
   # Remove duplicate ALERT-001 below, keep this one
   ```

4. **Resolve:**
   ```bash
   git add .ai/ALERTS.md
   git commit -m "docs: resolve merge conflict in ALERTS.md"
   ```

---

## Troubleshooting Multi-Agent Issues

### Q: Agent A updated CONTEXT.md but Agent B doesn't see it

**A:** Agent B didn't pull the latest changes.

```bash
git pull origin main
cat .ai/CONTEXT.md  # Now shows Agent A's updates
```

Or set up auto-pull in hooks:

```bash
# .git/hooks/post-merge
ai-orch triage  # Re-triage after every merge
```

---

### Q: Two agents are stuck in a loop: A waits for B, B waits for A

**A:** Use DISCUSSIONS.md to break the deadlock:

```markdown
## Deadlock: JWT refresh + OAuth

**Agent A**: Can't implement OAuth until JWT refresh is done  
**Agent B**: JWT refresh blocked on OAuth design decision  

**Resolution**: A will implement JWT refresh without async first.  
B can start OAuth in parallel using sync version. Refactor together later.
```

Implement the resolution:

```bash
ai-orch update --section "Current State" --value "- Breaking deadlock: A→JWT (sync), B→OAuth (parallel)"
ai-orch handoff
```

---

### Q: Agent A marked an alert as RESOLVED but it's still blocking Agent B

**A:** Alert resolution was incorrect. Check the fix:

```bash
grep -A5 "## RESOLVED" .ai/ALERTS.md | head -10
# See what was marked as resolved

git log -p .ai/ALERTS.md | grep -B5 -A5 "RESOLVED"
# See when/why it was moved to RESOLVED
```

If fix incomplete:

```markdown
## RESOLVED

### [ALERT-001] JWT refresh broken
**Resolution**: Agent A added refresh logic to auth.py.
**Date**: 2024-01-20
**Proof**: PR #45 merged

# But wait... testing shows it still fails in staging!
# Move back to P0
```

```bash
# Move back to P0 in ALERTS.md
nano .ai/ALERTS.md
# Cut from ## RESOLVED section
# Paste into ## P0 section

git add .ai/ALERTS.md
git commit -m "docs: reopen ALERT-001 — JWT refresh fails in staging"
```

---

## Best Practices

### Q: What's the best way to structure DISCUSSIONS.md?

**A:** Use threads by feature/area:

```markdown
# Discussions

## Thread: Authentication Module Refactoring

**Status**: In Progress  
**Owner**: Agent A  
**Goal**: Convert to async/await, add 2FA  

**Agent A (2024-01-15 09:00)**:  
Starting JWT refactor. Will take ~2 sessions.  
Blocked on Redis design decision (see DEC-004).

**Agent B (2024-01-15 14:00)**:  
Approved design. I can start 2FA in parallel once JWT is mergeable.  
Question: Will you add refresh token rotation?

**Agent A (2024-01-16 10:00)**:  
Yes, added to task. Refresh tokens rotate every 30 days.  
PR ready for review at #45.

---

## Thread: Database Query Performance

**Status**: Waiting  
**Owner**: None  
**Goal**: Index optimization for user queries  

**Agent C (2024-01-18)**:  
Profiled slow queries. Need to add indexes on (user_id, created_at).  
Requires Alembic migration. Who can implement?

**Agent B (2024-01-19)**:  
I'll take this. Can you provide the migration script?  
I'll test in staging before pushing.
```

---

### Q: How often should agents commit CONTEXT updates?

**A:** Commit whenever:

1. **At end of session** (mandatory):
   ```bash
   ai-orch handoff
   ```

2. **When starting significant work** (good practice):
   ```bash
   ai-orch update --section "Most recently changed" --value "- Starting async/await refactor of src/auth.py"
   git add .ai/CONTEXT.md && git commit -m "docs: claim auth.py for refactor"
   ```

3. **When hitting a blocker** (essential):
   ```bash
   ai-orch action-add "Design decision needed: REST vs GraphQL" --type other
   ai-orch handoff
   # Next agent knows where you got stuck
   ```

---

### Q: Should agents merge their own PRs?

**A:** No. Minimum for handoff:

```
1. Code changes committed to branch
2. .ai/CONTEXT.md updated describing changes  
3. .ai/ALERTS.md updated with new blockers
4. .ai/DECISIONS.md updated with design choices
5. PR created and linked in DISCUSSIONS.md

Then: Next agent reviews and merges (or takes over)
```

This forces knowledge transfer through documentation.

---

## When Things Go Wrong

### Q: CONTEXT.md has 10 conflicting merges

**A:** Simplify by resetting to main and re-documenting:

```bash
git checkout main -- .ai/CONTEXT.md
ai-orch triage  # Re-read current state
# Manually re-add your notes
git add .ai/CONTEXT.md && git commit -m "docs: reset context, manual re-sync"
```

---

### Q: We lost track of who's working on what

**A:** Rebuild from git history:

```bash
# See all recent handoffs
git log --oneline .ai/CONTEXT.md | head -10

# See who committed what
git log --all .ai/CONTEXT.md --pretty=format:"%h %an %s" | head -10

# Read last few sessions
git show HEAD~3:.ai/CONTEXT.md  # 3 commits ago
git show HEAD~2:.ai/CONTEXT.md  # 2 commits ago
git show HEAD~1:.ai/CONTEXT.md  # 1 commit ago

# Rebuild DISCUSSIONS.md summary
nano .ai/DISCUSSIONS.md
# Add thread: "Who did what" with git log references
```

---

## Integration with CI/CD

### Q: Can we automate CONTEXT updates in CI?

**A:** Yes. Example GitHub Actions workflow:

```yaml
name: Auto-update Snapshot on Main
on:
  push:
    branches: [main]

jobs:
  snapshot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
      - run: pip install ai-orchestrator
      - run: ai-orch snapshot --src src
      - name: Commit snapshot if changed
        run: |
          if git diff --quiet .ai/CONTEXT.md; then
            echo "No snapshot changes"
          else
            git add .ai/CONTEXT.md
            git commit -m "docs: auto-update codebase snapshot"
            git push
          fi
```

This keeps `.ai/CONTEXT.md` snapshot in sync automatically.

---

## Final Notes

1. **ORCHESTRATOR.md is mandatory** — Every agent must read it first
2. **Coordination beats speed** — 5 min to read context saves hours of redo
3. **Document decisions early** — DECISIONS.md prevents architecture conflicts
4. **Use DISCUSSIONS for debates** — WHEELS.md for what failed
5. **Commit CONTEXT updates frequently** — Let next agent pick up cleanly

See [README.md](../README.md) for quick start and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for specific issues.
