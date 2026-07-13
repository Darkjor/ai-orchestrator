# Manual de Usuario de AI Orchestrator (`ai-orch`)

> **Nota**: Este manual describe la versión `v0.3.0` del orquestador.

---

## 1. Filosofía: CEO Mode y Memoria Compartida

Cuando múltiples agentes de IA (o un mismo agente en distintas sesiones) colaboran en un repositorio, suelen enfrentar pérdida de contexto:
- Repetición de análisis costosos.
- Ignorancia de alertas críticas (bugs bloqueantes).
- Decisiones de diseño contradictorias.
- Sobreescritura de archivos sin registrar cambios semánticos.

`ai-orch` resuelve esto estableciendo una **memoria compartida** en el repositorio a través de la carpeta `.ai/`. Cualquier agente de IA que llegue al proyecto puede leer el archivo de llegada (`.ai/ORCHESTRATOR.md`) y el estado actual (`.ai/CONTEXT.md`) en menos de un minuto para ponerse en marcha sin repetir trabajo.

---

## 2. Estructura de la carpeta `.ai/`

El directorio `.ai/` sirve como la única fuente de verdad para la coordinación de agentes:

| Archivo | Propósito |
|---------|-----------|
| `ORCHESTRATOR.md` | Protocolo de llegada de CEO — lelo antes de empezar cualquier sesión. |
| `CONTEXT.md` | Estado en vivo del proyecto, qué funciona, qué no y últimos cambios. |
| `ALERTS.md` | Registro de incidencias abiertas divididas por prioridad (`P0`, `P1`, `P2`). |
| `PENDING.md` | Acciones manuales pendientes que requieren intervención humana fuera del código. |
| `DECISIONS.md` | Historial inmutable (append-only) de las decisiones arquitectónicas del proyecto. |
| `WHEELS.md` | Catálogo de dependencias, tecnologías en uso y experimentos fallidos (para evitar reinventar la rueda). |
| `DISCUSSIONS.md` | Tablón de debate y handoff asíncrono para agentes o humanos. |
| `config.json` | Configuración de enrutamiento de modelos de IA, agentes de análisis y observabilidad de Supabase. |
| `ANALYSIS.md` | Reporte de métricas auto-generado por el pipeline de análisis de agentes. |

---

## 3. Guía de Comandos de la CLI

El CLI de `ai-orch` provee 13 comandos agrupados por su propósito en el ciclo de desarrollo:

### Inicialización y Configuración

#### `ai-orch init`
Crea la carpeta `.ai/` con todas las plantillas estándar en el directorio de trabajo actual.
```bash
ai-orch init
```

#### `ai-orch hook-install`
Instala git hooks en `.git/hooks/` (pre-commit y post-commit). El hook de pre-commit ejecuta `ai-orch check` para impedir que se suban cambios sin actualizar `.ai/CONTEXT.md`. El hook de post-commit ejecuta `ai-orch snapshot` automáticamente para refrescar el mapa del codebase.
```bash
ai-orch hook-install
```

### Diagnóstico y Control de Git

#### `ai-orch triage`
Realiza un diagnóstico rápido de la salud del repositorio:
1. Comprueba si hay alertas activas en `.ai/ALERTS.md`.
2. Escanea conflictos de git pendientes.
3. Busca fugas de credenciales o archivos de entorno expuestos.
4. Ejecuta el comando de test configurado en `.ai/config.json`.
```bash
ai-orch triage
```

#### `ai-orch check`
Verifica si el commit actual respeta las reglas del proyecto. Valida que no se suban archivos de secretos y que se actualice `.ai/CONTEXT.md` si se modificaron archivos de código de producción. Devuelve código de salida `1` en caso de violación, bloqueando el commit de git.
```bash
ai-orch check
```

#### `ai-orch snapshot`
Genera un snapshot del codebase extrayendo las firmas de clases y funciones públicas de todos los archivos del proyecto y actualizando la sección `## Codebase Snapshot` en `.ai/CONTEXT.md`.
```bash
ai-orch snapshot
```

### Gestión de Tareas y Contexto

#### `ai-orch update <section> <value>`
Actualiza una sección en específico de forma programática en `.ai/CONTEXT.md`.
```bash
ai-orch update "Next Block — Planned" "- [ ] Implement features"
```

#### `ai-orch action-add <category> <title> [--target <target>]`
Añade una acción manual pendiente bajo la categoría provista (`Database`, `Infrastructure`, `Other`) en `.ai/PENDING.md`.
```bash
ai-orch action-add Other "Configurar API Keys de Supabase en producción"
```

#### `ai-orch action-resolve <id>`
Marca una acción manual específica como resuelta, moviéndola de su sección original a `## DONE` en `.ai/PENDING.md`.
```bash
ai-orch action-resolve ACTION-002
```

#### `ai-orch export [--out <file>]`
Consolida todos los archivos de contexto en `.ai/` en un único string estructurado de Markdown (ideal para alimentar a agentes con contexto denso).
```bash
ai-orch export --out full_context.md
```

#### `ai-orch handoff`
Inicia un asistente interactivo que guía al desarrollador o al agente al final de la sesión para documentar el tipo de tarea, los logros, los archivos modificados, agregar decisiones/alertas y hacer commit.
```bash
ai-orch handoff
```

### Pipeline de Análisis Verificable (Anti-alucinaciones)

#### `ai-orch analyze`
Recolecta métricas duras de forma determinista (cobertura de tests, alertas abiertas, acciones pendientes, modificaciones git) y escribe un reporte provisional en `.ai/ANALYSIS.md` con estado `PENDING`.
```bash
ai-orch analyze
```

#### `ai-orch qa [--override]`
Valida si los datos reportados en `.ai/ANALYSIS.md` coinciden exactamente con el estado actual del repositorio. Si hay discrepancias (por ejemplo, alertas que se resolvieron pero siguen figurando en el análisis), el comando falla y cambia el estado a `QA_ESCALATED`. Para forzar la aprobación del reporte se puede usar `--override`.
```bash
ai-orch qa
```

### Observabilidad y Monitoreo

#### `ai-orch observe`
Muestra las últimas ejecuciones registradas de la suite de agentes para el proyecto actual desde el backend de observabilidad (Supabase).
```bash
ai-orch observe
```

---

## 4. Pipeline de Análisis: Ciclo de Vida

Para garantizar la honestidad de la IA, los reportes de análisis no se consideran válidos hasta pasar la verificación de QA. El ciclo de vida del estado del reporte en `ANALYSIS.md` es:
```
[PENDING] ───(ai-orch qa)───> [QA_APPROVED]
    │
    └────────(mismatch)───────> [QA_ESCALATED] ───(ai-orch qa --override)───> [HUMAN_REVIEWED]
```

---

## 5. Configuración de Agentes y Observabilidad (`config.json`)

El archivo `.ai/config.json` define el comportamiento de los agentes de análisis y de la base de datos de observabilidad:

### Agentes
Define el rol y el enfoque del analizador y el revisor de QA:
- `analyzer`: Escribe el reporte.
- `qa_reviewer`: Audita y busca inconsistencias.

### Observabilidad
Si se configura Supabase, las ejecuciones de los comandos `analyze` y `qa` se registrarán automáticamente en la tabla correspondiente:
```json
  "observability": {
    "store": "supabase",
    "table": "agent_runs",
    "env_vars": {
      "url": "SUPABASE_URL",
      "key": "SUPABASE_ANON_KEY"
    },
    "thresholds": {
      "latency_warn_ms": 5000,
      "cost_warn_usd": 0.10,
      "error_rate_warn_pct": 10
    },
    "enabled": "auto"
  }
```
*Nota*: El paquete `supabase` es opcional; si falta o no se configuran las variables de entorno, la observabilidad se desactivará de forma silenciosa sin interrumpir la ejecución de la CLI.
