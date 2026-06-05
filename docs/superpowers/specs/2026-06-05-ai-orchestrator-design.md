# Design Spec: Global AI Orchestrator v2 Framework

**Date**: 2026-06-05  
**Author**: Antigravity AI  
**Status**: Proposal  

---

## 1. Goal & Context

When multiple AI agents (or the same agent across different sessions) work on a codebase, they face three major pain points:
1. **Context Loss**: No shared short-term memory between agent sessions (running out of tokens, session limits).
2. **Reinventing the Wheel**: Agents installing redundant packages or implementing custom utilities because they don't know what is already built, or recreating previously failed experiments.
3. **Fragile Collaboration**: No structured peer-review or handoff mechanism, causing agents to build features on top of broken/buggy code.

This project implements a **Global, Tech-Agnostic AI Orchestrator Framework** consisting of two main pillars:
1. An **agnostic documentation framework** under `.ai/` that acts as the "Arrival/Departure Dashboard" for AIs.
2. A **Python-based CLI tool** (`ai-orch`) that automates checks, triages the project, and streamlines handoffs.

---

## 2. Directory Structure (`.ai/` Boilerplate)

Every repository adopting the framework will have a `.ai/` folder at its root:

```
.ai/
├── ORCHESTRATOR.md   # Universal CEO Mode arrival & departure protocol (Agnostic)
├── CONTEXT.md        # Current project status, recent changes, and next block plan
├── ALERTS.md         # Active bugs/blockers classified by severity (P0 / P1 / P2)
├── DECISIONS.md      # Log of design & architecture decisions (DEC-XXX)
├── WHEELS.md         # Catalog of tools in use + failed experiments (WHEEL-XXX)
├── DISCUSSIONS.md    # Handoff and asynchronous debate board (THREAD-XXX)
└── config.json       # Project-specific metadata & validation commands
```

### File Schemas & Rules

#### `.ai/ORCHESTRATOR.md`
Instructs incoming agents to read `CONTEXT.md`, check `ALERTS.md`, and review `DISCUSSIONS.md` before claiming work. Enforces the departure checklist before they commit or close their session.

#### `.ai/WHEELS.md`
Prevents agents from reinventing utilities. Contains:
- **Core Stack & Libraries**: Authorized frameworks/utilities.
- **Failed Experiments**: Explains what was tried, why it failed, and what to do instead.

#### `.ai/DISCUSSIONS.md`
Enables asynchronous coordination. Agents open `[THREAD-XXX]` entries with context, proposals, and questions. Subsequent agents act as peer-reviewers, responding to threads, validating code modifications, and closing threads when resolved.

---

## 3. Python CLI Tool (`ai-orch`)

A globally installable Python command-line utility packaged using standard Python libraries, `typer` (CLI runner), and `rich` (terminal formatting).

### Key Commands

```bash
# 1. Bootstrapping
ai-orch init
```
- Creates `.ai/` in the current folder.
- Copies clean, agnostic templates.
- Genera `.ai/config.json`.

```bash
# 2. Local Health Triage
ai-orch triage
```
- Parses `.ai/ALERTS.md` and displays open P0/P1/P2 issues in a formatted `rich` table.
- Reads `.ai/config.json` and runs:
  - Git conflict check (searches files for `<<<<<<<`).
  - Exposed credential check (scans staged files for common keys/credentials).
  - Executable test check (runs the configured `test_command` like `npm test` or `pytest`).

```bash
# 3. Interactive Handoff
ai-orch handoff
```
- Launches an interactive wizard prompting the developer or agent for:
  - Accomplishments to append to `CONTEXT.md` ("What works right now").
  - Modified files to append to `CONTEXT.md` ("Most recently changed").
  - New alerts to append to `ALERTS.md`.
  - Design decisions to append to `DECISIONS.md`.
- Cleans and formats markdown files programmatically.
- Performs Git commit with structured template: `[Block N] type(scope): description`.

```bash
# 4. Git Pre-Commit Validation
ai-orch check
```
- Checks if files in the staging area have changed.
- If source code files are modified, verifies if `.ai/CONTEXT.md` (or another file in `.ai/`) was also modified in the staging area.
- Exits with `1` if the context update was omitted, halting the commit.

```bash
# 5. Git Hook Setup
ai-orch hook install
```
- Appends the `ai-orch check` call into `.git/hooks/pre-commit`.

---

## 4. Verification & Testing

### Automated Checks
- Unit tests for markdown parsers inside `ai-orch` (verifying programmatically reading/writing markdown headers and tables).
- CLI integration tests simulating `init`, `triage`, and `check` commands in a mock temporary git repository.

### Manual Verification
- Bootstrap a dummy project using `ai-orch init`.
- Introduce a mock P0 alert in `ALERTS.md` and confirm `ai-orch triage` reports it correctly.
- Stage a file modification without updating `.ai/CONTEXT.md` and verify `ai-orch check` blocks the git commit.
