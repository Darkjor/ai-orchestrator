# Wheels — <project_name>

> Lee este archivo ANTES de implementar cualquier cosa.
> Si lo que vas a hacer aparece como FAIL o ALUC — busca alternativa primero.

---

## 1. Stack Activo (no reinventar)

| Componente | Qué es | Dónde vive | Cómo usarlo |
|------------|--------|------------|-------------|
| Supabase | Store de observabilidad — agent runs, latencia, costo, estado | `src/aiorch/observability.py` → `SUPABASE_URL` + `SUPABASE_ANON_KEY` env vars | `from aiorch.observability import get_logger; get_logger().log_run(...)` |
| Rich / Typer | CLI output y comandos | `src/aiorch/main.py` | `console = Console(); app = typer.Typer()` |
| pytest | Tests — correr con `pytest` | `tests/test_cli.py` | `pytest` o `pytest tests/test_cli.py::test_name` |
| Ruflo / claude-flow | Memory vectorial cross-session | MCP tools vía ToolSearch | `memory_store`, `memory_search` |

---

## 2. QA Failures (lo que se intentó y no funcionó)

*(vacío al inicio — añadir cuando algo falle en QA o runtime)*

### Formato:

```
### [FAIL-XXX] Título corto

**Intentado**: descripción exacta de lo que se hizo
**Falló porque**: causa raíz, no síntoma
**Contexto**: tarea/fecha en que ocurrió
**Alternativa adoptada**: qué funcionó en su lugar
```

---

## 3. Alucinaciones Documentadas (patrones incorrectos de agentes)

*(vacío al inicio — añadir cuando un agente repita el mismo error)*

### Formato:

```
### [ALUC-XXX] Título corto

**El agente insiste en**: comportamiento incorrecto que repite
**Por qué está mal aquí**: razón específica de este proyecto
**Qué hacer en cambio**: instrucción directa
```

---

## 4. Lint Rules (enforced at pre-commit)

Rules here are checked automatically by `ai-orch check` against staged files.
Add a rule when a pattern from ALUC/FAIL needs to be enforced in code, not just documented.

### Rule format

```
### [LINT-001] Short description
**Pattern**: `regex_pattern`
**Files**: *.ext, *.ext2
**Message**: Why this is blocked and what to do instead.
```

No rules yet — add one when a WHEELS pattern needs hard enforcement.

---

## Cómo actualizar este archivo

**Cuando algo falla:** añadir `[FAIL-XXX]` con causa raíz + alternativa adoptada.

**Cuando un agente repite un error:** añadir `[ALUC-XXX]` con instrucción directa.

**Cuando un patrón de ALUC necesita enforcement duro:** añadir `[LINT-XXX]` en la sección 4.
