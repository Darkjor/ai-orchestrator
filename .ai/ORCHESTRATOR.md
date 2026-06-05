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
  → Do NOT start new work until P0 is handled.

Only P1/P2 alerts?
  → Note them. Proceed to step 3.

No alerts?
  → Proceed to step 3.
```

If you are unsure about severity → run `python -m aiorch.main triage`.

### Integrated Stack: ai-orch + Ruflo + Superpowers

This project runs three systems together. At session start, in order:

1. **Ruflo memory** — Recover context from last session:
   Use `memory_search` MCP tool to query "orquestador session context"
   (tool: `mcp__claude-flow__memory_search`)

2. **ai-orch triage** — Check project health:

   ```sh
   python -m aiorch.main triage
   ```

   Address any P0 alerts before writing code.

3. **Superpowers** — Before any creative/implementation work:
   Invoke `superpowers:brainstorming` skill for features,
   `superpowers:systematic-debugging` for bugs,
   `superpowers:subagent-driven-development` for multi-task plans.

At session END, in order:

1. Run `python -m aiorch.main handoff` (updates .ai/ docs + commits)
2. Store session summary in ruflo memory:
   Use `memory_store` MCP tool with namespace "orquestador" and key "last_session"

### Minute 3 — Identify yourself and claim work

→ See "Task Routing by AI Type" below.

### Before You Leave (mandatory)

Before ending your session, update:

| File | What to update |
|------|---------------|
| `.ai/CONTEXT.md` | Current State + Most Recently Changed |
| `.ai/ALERTS.md` | New fires discovered, resolved alerts |
| `.ai/DECISIONS.md` | Any architectural decision you made |

**If you run out of tokens mid-task**: update CONTEXT.md with exactly where you stopped.
The next AI will pick up from there.

---

## Cómo elegir tu herramienta

Lee `.ai/WHEELS.md` primero. Si lo que vas a hacer aparece como FAIL o ALUC, busca alternativa.

Luego identifica el tipo de tarea y usa la herramienta correcta:

| Tarea | Herramienta a invocar |
|-------|-----------------------|
| Feature nueva | `superpowers:brainstorming` → `superpowers:writing-plans` → `superpowers:subagent-driven-development` |
| Bug / comportamiento inesperado | `superpowers:systematic-debugging` |
| Múltiples tareas paralelas e independientes | `superpowers:dispatching-parallel-agents` |
| Tarea compleja con muchos subtareas | `sparc:orchestrator` o `swarm:swarm-init` (ruflo) |
| Necesitas un skill que no existe | `skill-creator:skill-creator` |
| Review de código | `superpowers:requesting-code-review` |
| Cualquier implementación de código | `superpowers:test-driven-development` (siempre, sin excepción) |
| Coordinación de múltiples agentes | `swarm:swarm-init` + `hive-mind:hive-mind-init` (ruflo) |
| Verificar que algo realmente funciona | `verify` skill |

**Número de agentes:** No hay número fijo. Usa los que la tarea requiera — puede ser 2 para un bugfix, 15 para una feature grande.

**Regla de oro:** WHEELS.md antes que código. Siempre.

### Flujo de sesión completo

```
LLEGADA
  1. [auto] memory_search "orquestador context" (ruflo)
     O leer .ai/CONTEXT.md + .ai/ALERTS.md si no tienes ruflo
  2. python -m aiorch.main triage
  3. Leer .ai/WHEELS.md — ¿qué NO hacer?

TRABAJO
  4. Identificar tipo de tarea → tabla arriba → invocar herramienta
  5. Antes de implementar: verificar contra WHEELS.md
  6. pytest tests/ -v debe estar verde antes de marcar done

SALIDA
  7. python -m aiorch.main handoff (actualiza .ai/ files)
  8. [auto] memory_store "orquestador context" con resumen de la sesión
  9. Si algo falló: añadir FAIL-XXX o ALUC-XXX a .ai/WHEELS.md
```

---

## Project Quick-Read

> **[PROJECT-SPECIFIC SECTION — update this when copying .ai/ to a new project]**

```
PROJECT: ai-orch (orquestador v1)
TYPE:    Python CLI — AI session orchestration framework
STATUS:  Alpha — 5 commands working, full stack integrated
STACK:   Python/Typer + Node/claude-flow MCP + Superpowers skills 5.1.0
RUN IT:  python -m aiorch.main triage
TESTS:   pytest tests/ -v (all passing)
TASKS:   .ai/CONTEXT.md + .ai/ALERTS.md
DOCS:    src/aiorch/main.py (442 lines), src/aiorch/templates/
BLOCKS:  Block 1 ✓ (init, triage, check, hook-install, handoff)
         Block 2 → ruflo integration, swarm agents, memory persistence
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

## Arriving From Another AI

### Claude Code (native)

No setup needed — follow the arrival protocol above.

### Gemini CLI

Feed context directly:
```sh
gemini "$(cat .ai/ORCHESTRATOR.md .ai/CONTEXT.md .ai/ALERTS.md)"
```
Then follow the arrival protocol as instructed.

### GPT-4 / ChatGPT

Paste this as your first message:
```
[START PROJECT CONTEXT]
[paste .ai/ORCHESTRATOR.md contents]
---
[paste .ai/CONTEXT.md contents]
---
[paste .ai/ALERTS.md contents]
[END PROJECT CONTEXT]
Follow the ARRIVAL PROTOCOL above. Adopt the appropriate Hat for your task.
```

### Cursor / GitHub Copilot

Add to `.cursorrules` or workspace instructions:
```
At the start of every session, read .ai/ORCHESTRATOR.md and follow the arrival protocol. Adopt the appropriate Hat.
```

### Any other AI

Feed `.ai/ORCHESTRATOR.md` + `.ai/CONTEXT.md` as system context before any task.

---

*Version: 2.0 — CEO Mode — 2026-06-05*
*Template — copy and adapt freely.*
