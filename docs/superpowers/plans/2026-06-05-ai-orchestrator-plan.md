# AI Orchestrator v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a global, tech-agnostic Python-based CLI tool `ai-orch` and documentation templates under `.ai/` to coordinate multiple AI agents asynchronously and prevent them from reinventing the wheel.

**Architecture:** A Python package (`aiorch`) using `typer` for CLI routing, `rich` for pretty output, and standard libraries for template copying, git verification, and file parsing.

**Tech Stack:** Python 3.10+, Typer, Rich, Git CLI.

---

## Proposed Changes

### Configuration & Package Setup
#### [NEW] [pyproject.toml](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/pyproject.toml)
#### [NEW] [src/aiorch/__init__.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/__init__.py)
#### [NEW] [src/aiorch/main.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/main.py)

### Boilerplate Templates
#### [NEW] [src/aiorch/templates/ORCHESTRATOR.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/ORCHESTRATOR.md)
#### [NEW] [src/aiorch/templates/CONTEXT.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/CONTEXT.md)
#### [NEW] [src/aiorch/templates/ALERTS.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/ALERTS.md)
#### [NEW] [src/aiorch/templates/DECISIONS.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/DECISIONS.md)
#### [NEW] [src/aiorch/templates/WHEELS.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/WHEELS.md)
#### [NEW] [src/aiorch/templates/DISCUSSIONS.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/DISCUSSIONS.md)
#### [NEW] [src/aiorch/templates/config.json](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/config.json)

### Tests
#### [NEW] [tests/test_cli.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/tests/test_cli.py)

---

## Detailed Tasks

### Task 1: Package Initialization & Structure
Define the project packaging and verify the test suite run.

- Create: [pyproject.toml](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/pyproject.toml)
- Create: [tests/test_cli.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/tests/test_cli.py)

- [ ] **Step 1: Create pyproject.toml**
  ```toml
  [project]
  name = "ai-orchestrator"
  version = "0.1.0"
  description = "A global, tech-agnostic AI Orchestrator CLI framework"
  requires-python = ">=3.10"
  dependencies = [
      "typer>=0.9.0",
      "rich>=13.0.0"
  ]

  [project.scripts]
  ai-orch = "aiorch.main:app"

  [build-system]
  requires = ["setuptools>=61.0.0"]
  build-backend = "setuptools.build_meta"
  ```
- [ ] **Step 2: Create empty tests file and main entrypoint**
  Create directory `src/aiorch` and `tests`. Create `src/aiorch/__init__.py` as empty.
  Create [tests/test_cli.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/tests/test_cli.py):
  ```python
  def test_placeholder():
      assert True
  ```
- [ ] **Step 3: Run test suite**
  Run: `pytest tests/test_cli.py`
  Expected: PASS
- [ ] **Step 4: Commit**
  Run: `git add pyproject.toml tests/test_cli.py && git commit -m "chore: initialize project packaging and test structure"`

---

### Task 2: Create Boilerplate Templates
Prepare the markdown files that will be copied by the `init` command.

- Create: [src/aiorch/templates/ORCHESTRATOR.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/ORCHESTRATOR.md)
- Create: [src/aiorch/templates/CONTEXT.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/CONTEXT.md)
- Create: [src/aiorch/templates/ALERTS.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/ALERTS.md)
- Create: [src/aiorch/templates/DECISIONS.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/DECISIONS.md)
- Create: [src/aiorch/templates/WHEELS.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/WHEELS.md)
- Create: [src/aiorch/templates/DISCUSSIONS.md](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/DISCUSSIONS.md)
- Create: [src/aiorch/templates/config.json](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/templates/config.json)

- [ ] **Step 1: Write all template files to `src/aiorch/templates/`**
  Ensure all documents are completely generic, referencing placeholder tags (e.g., `<project_name>`) and containing the guidelines we discussed.
- [ ] **Step 2: Commit templates**
  Run: `git add src/aiorch/templates/ && git commit -m "feat: add global documentation templates"`

---

### Task 3: Implement `ai-orch init`
Write the command to bootstrap the `.ai/` directory.

- Create/Modify: [src/aiorch/main.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/main.py)
- Modify: [tests/test_cli.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/tests/test_cli.py)

- [ ] **Step 1: Write a failing test for `init` command**
  Add to `tests/test_cli.py`:
  ```python
  import os
  from typer.testing import CliRunner
  from aiorch.main import app

  runner = CliRunner()

  def test_init_creates_ai_folder(tmp_path):
      os.chdir(tmp_path)
      result = runner.invoke(app, ["init"])
      assert result.exit_code == 0
      assert os.path.exists(".ai")
      assert os.path.exists(".ai/ORCHESTRATOR.md")
      assert os.path.exists(".ai/config.json")
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_cli.py -k test_init_creates_ai_folder`
  Expected: FAIL (No module main or command not found)
- [ ] **Step 3: Implement `init` command**
  In `src/aiorch/main.py`:
  ```python
  import os
  import shutil
  import json
  import typer
  from rich.console import Console

  app = typer.Typer(help="Global AI Orchestrator CLI")
  console = Console()

  @app.command()
  def init():
      """Initialize .ai/ orchestrator folder in current directory."""
      if os.path.exists(".ai"):
          console.print("[yellow]Warning: .ai directory already exists.[/yellow]")
          raise typer.Exit()
      
      os.makedirs(".ai", exist_ok=True)
      template_dir = os.path.join(os.path.dirname(__file__), "templates")
      for filename in os.listdir(template_dir):
          src = os.path.join(template_dir, filename)
          dst = os.path.join(".ai", filename)
          shutil.copy(src, dst)
      
      console.print("[green]Successfully initialized .ai/ orchestrator folder![/green]")

  if __name__ == "__main__":
      app()
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_cli.py -k test_init_creates_ai_folder`
  Expected: PASS
- [ ] **Step 5: Commit**
  Run: `git add src/aiorch/main.py tests/test_cli.py && git commit -m "feat: implement init command"`

---

### Task 4: Implement `ai-orch triage`
Implement parser for `ALERTS.md` and basic static file triage.

- Modify: [src/aiorch/main.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/main.py)
- Modify: [tests/test_cli.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/tests/test_cli.py)

- [ ] **Step 1: Write a test for parsing alerts and checking files**
  Add test checking that `triage` command identifies P0 alerts in a custom mock `ALERTS.md` and finds exposed credentials/merge conflicts.
- [ ] **Step 2: Run test to verify failure**
  Run: `pytest tests/test_cli.py -k test_triage`
  Expected: FAIL
- [ ] **Step 3: Implement `triage` command**
  Add `@app.command()` for `triage` in `main.py`. Parse `.ai/ALERTS.md` looking for headers like `### [ALERT-XXX]` and severity labels (`Severity: P0`). Scan files for `<<<<<<<` and `.env` files. Print results with `rich.table.Table`.
- [ ] **Step 4: Run test to verify success**
  Run: `pytest tests/test_cli.py -k test_triage`
  Expected: PASS
- [ ] **Step 5: Commit**
  Run: `git add src/aiorch/main.py tests/test_cli.py && git commit -m "feat: implement triage command"`

---

### Task 5: Implement `ai-orch check` & `hook install`
Create validation check to ensure `.ai/CONTEXT.md` changes when codebase files change, and automate git hook registration.

- Modify: [src/aiorch/main.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/main.py)
- Modify: [tests/test_cli.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/tests/test_cli.py)

- [ ] **Step 1: Write failing tests for git validation and hook installation**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `check` and `hook_install` commands**
  Use subprocess to call `git diff --cached --name-only`. If source files (excluding `.ai/`) are modified but no files in `.ai/` are modified, print an error and exit `1`.
  `hook_install` writes `ai-orch check` to `.git/hooks/pre-commit` and calls `chmod +x` on it.
- [ ] **Step 4: Run test to verify success**
- [ ] **Step 5: Commit**
  Run: `git add src/aiorch/main.py tests/test_cli.py && git commit -m "feat: implement check and hook install commands"`

---

### Task 6: Implement `ai-orch handoff`
Build interactive wizard using `typer.prompt` to gather task accomplishments and update markdown structures.

- Modify: [src/aiorch/main.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/src/aiorch/main.py)
- Modify: [tests/test_cli.py](file:///c:/Users/Perez/OneDrive/Escritorio/Projects/orquestador%20v1/tests/test_cli.py)

- [ ] **Step 1: Write tests for markdown file manipulation**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `handoff` command**
  Gather input and modify `.ai/CONTEXT.md` (injecting to `What works right now` and `Most recently changed` headers) and append decisions to `DECISIONS.md`. Optionally commit changes.
- [ ] **Step 4: Run test to verify success**
- [ ] **Step 5: Commit**
  Run: `git add src/aiorch/main.py tests/test_cli.py && git commit -m "feat: implement handoff wizard command"`

---

## Verification Plan

### Automated Tests
Run entire test suite:
`pytest tests/`

### Manual Verification
1. Create a dummy git repo: `git init dummy-repo`
2. Install local package: `pip install -e .`
3. Run `ai-orch init` inside `dummy-repo`
4. Run `ai-orch hook install`
5. Modify a dummy file, stage it, and verify that `git commit` fails until `.ai/CONTEXT.md` is updated.
