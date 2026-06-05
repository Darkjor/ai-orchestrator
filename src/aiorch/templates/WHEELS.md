# Wheels — <project_name>

> Lee este archivo ANTES de implementar cualquier cosa.
> Si lo que vas a hacer aparece como FAIL o ALUC — busca alternativa primero.

---

## 1. Stack Activo (no reinventar)

| Componente | Qué es | Dónde vive | Cómo usarlo |
|------------|--------|------------|-------------|
| (añadir componentes del proyecto aquí) | | | |

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

## Cómo actualizar este archivo

**Cuando algo falla:** añadir `[FAIL-XXX]` con causa raíz + alternativa adoptada.

**Cuando un agente repite un error:** añadir `[ALUC-XXX]` con instrucción directa.
