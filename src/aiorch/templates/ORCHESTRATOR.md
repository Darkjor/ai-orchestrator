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

> **QA agents / deep analysis:** Run `ai-orch export` first to get the full context bundle
> instead of reading CONTEXT.md alone. CONTEXT.md is the 80-line executive brief;
> `ai-orch export` gives you every `.ai/` file consolidated.

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

---

## Cómo elegir tu herramienta

Lee `.ai/WHEELS.md` primero. Si lo que vas a hacer aparece como FAIL o ALUC, busca alternativa.

| Tarea | Herramienta a invocar |
|-------|-----------------------|
| Feature nueva | `superpowers:brainstorming` → `writing-plans` → `subagent-driven-development` |
| Bug / comportamiento inesperado | `superpowers:systematic-debugging` |
| Múltiples tareas paralelas | `superpowers:dispatching-parallel-agents` |
| Tarea compleja con muchos subtareas | `sparc:orchestrator` o `swarm:swarm-init` (ruflo) |
| Necesitas un skill nuevo | `skill-creator:skill-creator` |
| Review de código | `superpowers:requesting-code-review` |
| Cualquier implementación | `superpowers:test-driven-development` (siempre) |
| Múltiples agentes coordinados | `swarm:swarm-init` + `hive-mind:hive-mind-init` |

**Número de agentes:** No hay número fijo. Usa los que la tarea requiera.

**Regla de oro:** WHEELS.md antes que código.

### Flujo de sesión completo

```
LLEGADA
  1. memory_search "<project> context" (ruflo) O leer .ai/CONTEXT.md + .ai/ALERTS.md
  2. <run_command> triage
  3. Leer .ai/WHEELS.md

TRABAJO
  4. Identificar tarea → tabla arriba → invocar herramienta correcta
  5. Verificar contra WHEELS.md antes de implementar
  6. Tests deben estar verdes antes de marcar done

SALIDA
  7. ai-orch handoff (actualiza .ai/ files)
  8. memory_store "<project> context" con resumen
  9. Si algo falló: añadir FAIL-XXX o ALUC-XXX a .ai/WHEELS.md
```

---

## Arriving From Another AI

### Claude Code (native)
No setup needed — follow the arrival protocol above.

### Gemini CLI
```sh
gemini "$(cat .ai/ORCHESTRATOR.md .ai/CONTEXT.md .ai/ALERTS.md .ai/WHEELS.md)"
```

### GPT-4 / ChatGPT
Paste `.ai/ORCHESTRATOR.md` + `.ai/CONTEXT.md` + `.ai/WHEELS.md` as your first message, then follow the arrival protocol.

### Cursor / GitHub Copilot
Add to `.cursorrules`: `At start of every session, read .ai/ORCHESTRATOR.md and follow the arrival protocol.`

### Any other AI
Feed `.ai/ORCHESTRATOR.md` + `.ai/CONTEXT.md` + `.ai/WHEELS.md` as system context before any task.
