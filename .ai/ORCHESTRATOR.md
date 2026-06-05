# AI Orchestrator v2 — CEO Mode

> You are arriving at this project as an intelligent agent.
> Do not jump into tasks. Do not start coding. Run the arrival protocol first.
> This takes 5 minutes and saves hours of misdirected work.

---

## ARRIVAL PROTOCOL — All AIs, Always, No Exceptions

### Minute 1 — Read the situation
1. Read `.ai/CONTEXT.md` — what works, what's broken, what changed last (60 sec)
2. Read `.ai/ALERTS.md` — what's on fire right now

### Minute 2 — Triage decision

```
P0 alert exists AND affects your capability?
  → Go to ALERTS.md. Fix the P0 or document why you can't.
  → Do NOT touch AI_TASKS.md until P0 is handled.

Only P1/P2 alerts?
  → Note them. Proceed to step 3.

No alerts?
  → Proceed to step 3.
```

If you are unsure about severity → run `.ai/TRIAGE.md` health checks.

### Minute 3 — Identify yourself and claim work

→ See "Task Routing by AI Type" below.

### Before You Leave (mandatory)

Before ending your session, update:

| File | What to update |
|------|---------------|
| `.ai/CONTEXT.md` | Current State + Most Recently Changed |
| `.ai/ALERTS.md` | New fires discovered, resolved alerts |
| `AI_TASKS.md` | Task status (claimed → in-progress → done) |
| `CHANGELOG.md` | What you shipped under [Unreleased] |
| `.ai/DECISIONS.md` | Any architectural decision you made |

**If you run out of tokens mid-task**: update CONTEXT.md with exactly where you stopped.
The next AI will pick up from there.

---

## Task Routing by AI Type

### You are a CODE AI
*(Claude Code, Gemini CLI, Cursor, Copilot, GPT-4o with code tools)*

1. Read `docs/HANDOFF.md` — architecture and stack (5 min)
2. Read `AI_TASKS.md` — find an Open task tagged `[code]`
3. Claim it: write your AI name + date in "Assigned to"
4. Follow the output paths in the task exactly
5. When done: update all departure files (see above)
6. Commit: `git commit -m "feat/fix/chore(scope): description [Block N]"`

**Hard rules:**
- Keep files ≤ 500 lines — split into modules if needed
- Never commit .env, secrets, or credentials
- Run existing tests before marking a task Done
- If blocked: document in ALERTS.md and AI_TASKS.md, don't just stop silently

### You are an IMAGE AI
*(Gemini Imagen, DALL-E, Midjourney, Stable Diffusion, Firefly)*

1. Read `docs/ASSET_GUIDE.md` — exact dimensions, format, style
2. Read `AI_TASKS.md` — find an Open task tagged `[image]`
3. Claim it
4. Generate → overwrite files in place. NEVER rename, move, or delete files.
5. When done: update departure files

**Hard rules:**
- PNG only with alpha channel
- Dimensions must match ASSET_GUIDE.md exactly
- Never touch .gd, .tscn, .go, .sql, .yaml, .json files
- Do not create new files unless the task explicitly lists them

### You are a TEXT / REASONING AI
*(GPT-4 chat, Gemini Pro, Claude chat without tools)*

1. Read `docs/HANDOFF.md` + `docs/PROGRESS.md`
2. Read `AI_TASKS.md` — find an Open task tagged `[analysis]` or `[docs]`
3. Claim it, complete it
4. Update departure files

---

## Project Quick-Read

> **[PROJECT-SPECIFIC SECTION — update this when copying .ai/ to a new project]**

```
PROJECT: Nexus RPG
TYPE:    MMORPG — Godot 4 client + Go authoritative server
STATUS:  Block 2 complete — offline demo fully playable
STACK:   GDScript / Go 1.22 / PostgreSQL 16 / Redis 7 / Nakama 3.22
RUN IT:  Godot 4 → Import client/ → F5 → "Jugar Demo (sin servidor)"
BLOCKER: ALERT-001 — Docker needs VT-x in BIOS (server can't run yet)
TASKS:   AI_TASKS.md
DOCS:    docs/HANDOFF.md (arch), docs/PROGRESS.md (sprint), .ai/DECISIONS.md (why)
BLOCKS:  Block 1 ✓ (camera fix, combat) | Block 2 ✓ (patrol, spells, inventory)
         Block 3 → sprite integration, server setup, multiplayer
```

---

## Reusing in Other Projects

The only project-specific content in this folder:
- **This file** → Project Quick-Read block (3 lines to update)
- **ALERTS.md** → all content (every project has different fires)
- **DECISIONS.md** → all content (every project has different decisions)
- **CONTEXT.md** → all content (project state)

Everything else (TRIAGE.md, protocols, routing rules, departure checklist) is **100% generic**.

**Bootstrap for a new project:**
```
1. Copy .ai/ folder to your new project root
2. Update ORCHESTRATOR.md → Project Quick-Read block
3. Clear ALERTS.md → add your project's known blockers
4. Clear DECISIONS.md → add your project's key decisions
5. Update CONTEXT.md → describe current state
6. Done — any AI arriving will immediately know what to do
```

---

## Compatibility

| AI Tool | First command |
|---------|--------------|
| Claude Code | Reads ORCHESTRATOR.md via Agent tool or context |
| Gemini CLI | `gemini "Read .ai/ORCHESTRATOR.md and follow the arrival protocol"` |
| GPT-4 / ChatGPT | Paste ORCHESTRATOR.md + CONTEXT.md as first message |
| Cursor | Add to `.cursorrules`: `Start every session by reading .ai/ORCHESTRATOR.md` |
| GitHub Copilot | Add to workspace instructions |
| Any other AI | Provide .ai/ORCHESTRATOR.md as system context |

---

*Version: 2.0 — CEO Mode — 2026-06-05*
*Template — copy and adapt freely.*
