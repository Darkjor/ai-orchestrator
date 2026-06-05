# Wheels — ai-orch (orquestador v1)

> Lee este archivo ANTES de implementar cualquier cosa.
> Si lo que vas a hacer aparece como FAIL o ALUC — busca alternativa primero.

---

## 1. Stack Activo (no reinventar)

| Componente | Qué es | Dónde vive | Cómo usarlo |
|------------|--------|------------|-------------|
| CLI Framework | `typer>=0.9.0` | `src/aiorch/main.py` | `@app.command()` — NO usar argparse ni click |
| Terminal UI | `rich>=13.0.0` | `src/aiorch/main.py:13` | `console = Console()` — todo output via `console.print()` |
| Agent Orchestration | Ruflo (claude-flow) MCP | `.mcp.json` | `npx ruflo@latest mcp start` — tools: `mcp__claude-flow__*` |
| Skills System | Superpowers 5.1.0 | `.claude/skills/` | Invocar via `Skill` tool en Claude Code |
| Testing | pytest | `tests/test_cli.py` | `pytest tests/ -v` — 14 tests, todos deben pasar |
| Package entry | `ai-orchestrator` | `pyproject.toml` | Entry point `ai-orch` → `aiorch.main:app` |
| Alert parsing | `parse_alerts()` | `src/aiorch/main.py:15` | Retorna `list[dict]` con id/title/severity/status |
| Template copy | `shutil.copy()` | `src/aiorch/main.py` (init) | Patrón para copiar templates a `.ai/` |
| Git subprocess | `subprocess.run()` | `src/aiorch/main.py` | `capture_output=True, text=True` siempre |

---

## 2. QA Failures (lo que se intentó y no funcionó)

### [FAIL-001] Substring match para detección de merge conflicts

**Intentado**: `if "<<<<<<<" in content and "=======" in content`
**Falló porque**: El scanner detectó sus propios string literals en `main.py` — la línea de código que contiene `"<<<<<<<"` como string es detectada como conflicto real. Falso positivo en cada `triage`.
**Contexto**: Implementado en `src/aiorch/main.py:139`, descubierto en sesión 2026-06-05.
**Alternativa adoptada**: `re.search(r'^<{7}', content, re.MULTILINE)` — los marcadores reales de conflicto siempre están al inicio de línea (DEC-004).

---

## 3. Alucinaciones Documentadas (patrones incorrectos que los agentes repiten)

*(vacío por ahora — añadir cuando se detecte un patrón repetido)*

### Formato para añadir una alucinación:

```
### [ALUC-XXX] Título corto

**El agente insiste en**: descripción exacta del comportamiento incorrecto
**Por qué está mal aquí**: razón específica de este proyecto/contexto
**Qué hacer en cambio**: instrucción directa y concreta
```

---

## Cómo actualizar este archivo

**Cuando algo falla en QA o en runtime:**
1. Añadir entrada `[FAIL-XXX]` en sección 2 con causa raíz real
2. Documentar la alternativa adoptada

**Cuando un agente repite el mismo error:**
1. Documentar el patrón en `[ALUC-XXX]` en sección 3
2. Dar instrucción directa de qué hacer en cambio
