import os
import shutil
import json
import re
import datetime
import subprocess
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help="Global AI Orchestrator CLI")
console = Console()

def parse_alerts(alerts_path: str):
    """Parse alerts file and return open P0, P1, P2 alerts."""
    if not os.path.exists(alerts_path):
        return []
    
    alerts = []
    current_severity = "P2"
    
    with open(alerts_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## P0"):
            current_severity = "P0"
        elif stripped.startswith("## P1"):
            current_severity = "P1"
        elif stripped.startswith("## P2"):
            current_severity = "P2"
        elif stripped.startswith("## RESOLVED"):
            current_severity = "RESOLVED"
        
        if stripped.startswith("### [ALERT-"):
            match = re.search(r"### \[(ALERT-\d+)\]\s*(.*)", stripped)
            if match:
                alert_id = match.group(1)
                title = match.group(2)
                if current_severity != "RESOLVED":
                    alerts.append({
                        "id": alert_id,
                        "title": title,
                        "severity": current_severity,
                        "status": "Open"
                    })
    return alerts

def detect_project_context(root: str = "."):
    """Detect project name, type, stack, and run/test commands from manifest files."""
    detected = {
        "project_name": os.path.basename(os.path.abspath(root)),
        "project_type": "Unknown",
        "project_stack": "Unknown",
        "run_command": "echo 'Run command not configured'",
        "test_command": "echo 'Test command not configured'",
    }

    package_json = os.path.join(root, "package.json")
    pyproject = os.path.join(root, "pyproject.toml")
    go_mod = os.path.join(root, "go.mod")
    cargo_toml = os.path.join(root, "Cargo.toml")

    if os.path.exists(package_json):
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            detected["project_name"] = data.get("name", detected["project_name"])
            detected["project_stack"] = "Node.js"
            detected["project_type"] = "CLI" if "bin" in data else "Library/App"
            scripts = data.get("scripts", {})
            if "test" in scripts:
                detected["test_command"] = "npm test"
            if "start" in scripts:
                detected["run_command"] = "npm start"
            elif "dev" in scripts:
                detected["run_command"] = "npm run dev"
        except Exception:
            pass
    elif os.path.exists(pyproject):
        try:
            with open(pyproject, "r", encoding="utf-8") as f:
                content = f.read()
            name_match = re.search(r'(?m)^name\s*=\s*"([^"]+)"', content)
            if name_match:
                detected["project_name"] = name_match.group(1)
            detected["project_stack"] = "Python"
            script_match = re.search(r"\[project\.scripts\]\s*\n\s*([\w-]+)\s*=", content)
            if script_match:
                detected["project_type"] = "CLI"
                detected["run_command"] = f"{script_match.group(1)} --help"
            else:
                detected["project_type"] = "Library"
            if os.path.exists(os.path.join(root, "tests")):
                detected["test_command"] = "pytest"
        except Exception:
            pass
    elif os.path.exists(go_mod):
        detected["project_stack"] = "Go"
        detected["project_type"] = "CLI/Library"
        detected["run_command"] = "go run ."
        detected["test_command"] = "go test ./..."
    elif os.path.exists(cargo_toml):
        detected["project_stack"] = "Rust"
        detected["project_type"] = "CLI/Library"
        detected["run_command"] = "cargo run"
        detected["test_command"] = "cargo test"

    return detected

@app.command()
def init():
    """Initialize .ai/ orchestrator folder and AGENTS.md in current directory."""
    if os.path.exists(".ai"):
        console.print("[yellow]Warning: .ai directory already exists.[/yellow]")
        raise typer.Exit()

    os.makedirs(".ai", exist_ok=True)
    template_dir = os.path.join(os.path.dirname(__file__), "templates")

    if not os.path.exists(template_dir):
        console.print(f"[red]Error: Templates directory {template_dir} not found.[/red]")
        raise typer.Exit(1)

    for filename in os.listdir(template_dir):
        src = os.path.join(template_dir, filename)
        if filename == "AGENTS.md":
            dst = "AGENTS.md"
            if os.path.exists(dst):
                console.print("[yellow]Warning: AGENTS.md already exists at project root, leaving it untouched.[/yellow]")
                continue
        else:
            dst = os.path.join(".ai", filename)
        shutil.copy(src, dst)

    detected = detect_project_context()
    config_path = os.path.join(".ai", "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config.update(detected)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
        console.print(f"[cyan]Detected project: {detected['project_name']} ({detected['project_stack']})[/cyan]")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not auto-fill .ai/config.json. Reason: {e}[/yellow]")

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    context_path = os.path.join(".ai", "CONTEXT.md")
    try:
        with open(context_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(
            r"## Current State \(updated: [^\)]+\)",
            f"## Current State (updated: {today_str})",
            content,
        )
        with open(context_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

    console.print("[green]Successfully initialized .ai/ orchestrator folder and AGENTS.md![/green]")

@app.command()
def triage():
    """Triage active project alerts and check codebase health."""
    if not os.path.exists(".ai"):
        console.print("[red]Error: .ai/ orchestrator folder not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)
        
    alerts_path = os.path.join(".ai", "ALERTS.md")
    alerts = parse_alerts(alerts_path)
    
    console.print(Panel("[bold blue]AI Orchestrator — Project Triage[/bold blue]", expand=False))
    
    if alerts:
        table = Table(title="Active Alerts", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=12)
        table.add_column("Severity", style="bold")
        table.add_column("Title")
        table.add_column("Status", justify="right")

        for alert in alerts:
            sev_color = "red" if alert["severity"] == "P0" else ("yellow" if alert["severity"] == "P1" else "blue")
            table.add_row(
                alert["id"],
                f"[{sev_color}]{alert['severity']}[/{sev_color}]",
                alert["title"],
                "[green]Open[/green]"
            )
        console.print(table)
    else:
        console.print("[green][OK] No active alerts found in ALERTS.md[/green]")

    console.print("\n[bold]Recommended Claude Models[/bold]")
    config_path = os.path.join(".ai", "config.json")
    models_config = None
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            models_config = config.get("models", {})
        except Exception:
            pass

    if models_config:
        default_model = models_config.get("default", "claude-sonnet-4-6")
        recommendations = models_config.get("recommendations", {})
        reasoning_tasks = models_config.get("reasoning_tasks", [])

        console.print(f"Default: [cyan]{default_model}[/cyan]")
        if recommendations:
            for task_type, model in recommendations.items():
                reasoning_note = " (with extended thinking)" if task_type in reasoning_tasks else ""
                console.print(f"  {task_type}: [yellow]{model}{reasoning_note}[/yellow]")
    else:
        console.print("[dim]No model recommendations configured in .ai/config.json[/dim]")
        
    console.print("\n[bold]Checking for git merge conflicts...[/bold]")
    conflict_found = False
    for root, dirs, files in os.walk("."):
        if any(ignored in root for ignored in [".git", "venv", ".venv", "node_modules", "__pycache__", ".pytest_cache"]):
            continue
        for file in files:
            file_path = os.path.join(root, file)
            if not file.endswith((".py", ".gd", ".go", ".js", ".ts", ".json", ".md", ".txt", ".html", ".xml", ".yml", ".yaml")):
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if re.search(r'^<{7}', content, re.MULTILINE) and re.search(r'^={7}$', content, re.MULTILINE):
                        console.print(f"[red][ERROR] Merge conflict found in {file_path}[/red]")
                        conflict_found = True
            except Exception:
                pass
    if not conflict_found:
        console.print("[green][OK] No active merge conflicts detected.[/green]")
        
    console.print("\n[bold]Checking for exposed secrets...[/bold]")
    staged_secrets = []
    if os.path.exists(".git"):
        try:
            res = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True)
            staged_files = res.stdout.splitlines()
            for f in staged_files:
                if f.endswith(".env") or "secret" in f.lower() or f.endswith(".pem") or f.endswith(".key"):
                    staged_secrets.append(f)
        except Exception:
            pass
            
    for f in os.listdir("."):
        if f.endswith(".env") or f.endswith(".pem") or f.endswith(".key"):
            staged_secrets.append(f)
            
    if staged_secrets:
        for sec in set(staged_secrets):
            console.print(f"[yellow][WARN] Warning: Potential secret file detected: {sec}[/yellow]")
    else:
        console.print("[green][OK] No secret/credential leaks detected.[/green]")

    config_path = os.path.join(".ai", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            test_cmd = config.get("test_command")
            if test_cmd:
                console.print(f"\n[bold]Running test command: {test_cmd}...[/bold]")
                test_res = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
                if test_res.returncode == 0:
                    console.print("[green][OK] Tests passed successfully![/green]")
                else:
                    console.print(f"[red][ERROR] Test command failed with exit code {test_res.returncode}[/red]")
                    if test_res.stdout:
                        console.print(test_res.stdout)
                    if test_res.stderr:
                        console.print(test_res.stderr)
        except Exception as e:
            console.print(f"[yellow][WARN] Warning: Could not run test command. Reason: {e}[/yellow]")

@app.command()
def check():
    """Verify that .ai context is updated when other changes are staged."""
    if not os.path.exists(".git"):
        console.print("[yellow]Not a git repository. Skipping context check.[/yellow]")
        raise typer.Exit(0)
        
    try:
        res = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True)
        staged_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception as e:
        console.print(f"[yellow]Git check failed: {e}. Skipping.[/yellow]")
        raise typer.Exit(0)
        
    if not staged_files:
        raise typer.Exit(0)
        
    codebase_changed = False
    ai_changed = False
    
    for f in staged_files:
        if f.startswith(".ai/") or f == "AGENTS.md":
            ai_changed = True
        elif not any(f.startswith(prefix) for prefix in [".git", "docs/"]):
            if f not in [".gitignore", "pyproject.toml"]:
                codebase_changed = True
                
    if codebase_changed and not ai_changed:
        console.print(Panel(
            "[red]Error: Staged files detected but .ai/ documentation context was not updated.[/red]\n\n"
            "Please run [bold]ai-orch handoff[/bold] or manually update [bold].ai/CONTEXT.md[/bold] "
            "to describe your changes before committing.",
            title="AI Orchestrator Guard",
            expand=False
        ))
        raise typer.Exit(1)
        
    console.print("[green][OK] AI orchestrator context update verified.[/green]")
    raise typer.Exit(0)

@app.command("hook-install")
def hook_install():
    """Install git pre-commit hook to automate context checking."""
    if not os.path.exists(".git"):
        console.print("[red]Error: Not a git repository. Run 'git init' first.[/red]")
        raise typer.Exit(1)
        
    hook_dir = os.path.join(".git", "hooks")
    os.makedirs(hook_dir, exist_ok=True)
    hook_path = os.path.join(hook_dir, "pre-commit")
    
    hook_content = """#!/bin/sh
# AI Orchestrator pre-commit validation hook

if command -v ai-orch >/dev/null 2>&1; then
  ai-orch check
else
  python -m aiorch.main check
fi
"""
    
    with open(hook_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(hook_content)
        
    try:
        os.chmod(hook_path, 0o755)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not set executable permission on hook. Reason: {e}[/yellow]")
        
    console.print(f"[green][OK] Git pre-commit hook installed at {hook_path}[/green]")

@app.command()
def handoff():
    """Run interactive handoff wizard to update .ai documentation and commit changes."""
    if not os.path.exists(".ai"):
        console.print("[red]Error: .ai/ orchestrator folder not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)
        
    console.print(Panel("[bold green]AI Orchestrator — Session Handoff Wizard[/bold green]", expand=False))

    config_path = os.path.join(".ai", "config.json")
    models_config = None
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            models_config = config.get("models", {})
        except Exception:
            pass

    # 1. Task Type Selection
    valid_task_types = ["architecture", "code_review", "refactoring", "bugfix", "feature", "tests", "docs"]
    task_type = typer.prompt(
        "What type of work did you complete? (architecture/code_review/refactoring/bugfix/feature/tests/docs)",
        default="feature"
    )
    if task_type not in valid_task_types:
        task_type = "feature"

    if models_config:
        recommended_model = models_config.get("recommendations", {}).get(task_type, models_config.get("default", "claude-sonnet-4-6"))
        reasoning_tasks = models_config.get("reasoning_tasks", [])
        console.print(f"\n[cyan]ℹ Recommended model: {recommended_model}[/cyan]")
        if task_type in reasoning_tasks:
            console.print("[yellow]✓ This task benefits from extended thinking mode[/yellow]")

    # 2. Accomplishments
    accomplishments = typer.prompt("What was accomplished in this block? (comma-separated, or empty to skip)", default="", show_default=False)

    # 3. Changed files
    changed_files = typer.prompt("What files or components were recently changed? (comma-separated, or empty to skip)", default="", show_default=False)

    # 4. Blocker/Alert
    add_alert = typer.confirm("Do you want to add a new blocker/alert?", default=False)
    new_alert_data = None
    if add_alert:
        alert_id = typer.prompt("Alert ID (e.g. ALERT-002)")
        alert_title = typer.prompt("Short description")
        alert_severity = typer.prompt("Severity (P0 / P1 / P2)", default="P2")
        new_alert_data = {
            "id": alert_id,
            "title": alert_title,
            "severity": alert_severity.upper()
        }

    # 5. Design Decision
    add_decision = typer.confirm("Do you want to document a new design decision?", default=False)
    new_dec_data = None
    if add_decision:
        dec_id = typer.prompt("Decision ID (e.g. DEC-002)")
        dec_title = typer.prompt("Short title")
        dec_context = typer.prompt("Decision context / rationale")
        new_dec_data = {
            "id": dec_id,
            "title": dec_title,
            "context": dec_context
        }

    # 6. Git Commit
    make_commit = typer.confirm("Do you want to stage all changes and create a git commit?", default=False)
    commit_data = None
    if make_commit:
        block_num = typer.prompt("Block number (e.g. 3)")
        commit_type = typer.prompt("Commit type (feat/fix/chore/docs)")
        commit_msg = typer.prompt("Commit message description")
        commit_data = {
            "block": block_num,
            "type": commit_type,
            "msg": commit_msg
        }

    # --- PROCESS UPDATES ---
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # Update CONTEXT.md
    context_path = os.path.join(".ai", "CONTEXT.md")
    if os.path.exists(context_path):
        with open(context_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        content = re.sub(
            r"## Current State \(updated: [^\)]+\)", 
            f"## Current State (updated: {today_str})", 
            content
        )
        
        if accomplishments:
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if "**What works right now:**" in line:
                    new_bullets = [f"- {acc.strip()}" for acc in accomplishments.split(",") if acc.strip()]
                    lines = lines[:i+1] + new_bullets + lines[i+1:]
                    break
            content = "\n".join(lines)
            
        if changed_files:
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if "**Most recently changed:**" in line:
                    new_bullets = [f"- {cf.strip()}" for cf in changed_files.split(",") if cf.strip()]
                    next_sec_idx = len(lines)
                    for j in range(i+1, len(lines)):
                        if lines[j].strip().startswith("---") or lines[j].strip().startswith("##"):
                            next_sec_idx = j
                            break
                    lines = lines[:i+1] + new_bullets + lines[next_sec_idx:]
                    break
            content = "\n".join(lines)
            
        with open(context_path, "w", encoding="utf-8") as f:
            f.write(content)
        console.print("[green][OK] Updated .ai/CONTEXT.md[/green]")

    # Update ALERTS.md
    if new_alert_data:
        alerts_path = os.path.join(".ai", "ALERTS.md")
        if os.path.exists(alerts_path):
            with open(alerts_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            header_pattern = f"## {new_alert_data['severity']}"
            inserted = False
            for i, line in enumerate(lines):
                if header_pattern in line:
                    alert_md = (
                        f"\n### [{new_alert_data['id']}] {new_alert_data['title']}\n"
                        f"**Severity**: {new_alert_data['severity']}\n"
                        f"**Status**:   Open\n"
                        f"**Owner**:    None\n"
                        f"**Discovered**: {today_str}\n"
                        f"**Impact**: [TBD]\n"
                        f"**Fix**: [TBD]\n"
                    )
                    lines.insert(i+1, alert_md)
                    inserted = True
                    break
            if inserted:
                with open(alerts_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                console.print(f"[green][OK] Added alert {new_alert_data['id']} to .ai/ALERTS.md[/green]")

    # Update DECISIONS.md
    if new_dec_data:
        decisions_path = os.path.join(".ai", "DECISIONS.md")
        if os.path.exists(decisions_path):
            decision_md = (
                f"\n## [{new_dec_data['id']}] {new_dec_data['title']}\n"
                f"**Date**: {today_str}\n"
                f"**Status**: Active\n"
                f"**Context**: {new_dec_data['context']}\n"
                f"**Decision**: [TBD]\n"
                f"**Rationale**: [TBD]\n"
                f"**Consequences**: [TBD]\n"
                f"**Revisit when**: [TBD]\n"
            )
            with open(decisions_path, "a", encoding="utf-8") as f:
                f.write(decision_md)
            console.print(f"[green][OK] Recorded decision {new_dec_data['id']} in .ai/DECISIONS.md[/green]")

    # Process Git commit
    if commit_data:
        try:
            # Stage everything
            subprocess.run(["git", "add", "."], check=True)
            # Commit
            commit_msg_full = f"[{commit_data['block']}] {commit_data['type']}: {commit_data['msg']}"
            subprocess.run(["git", "commit", "-m", commit_msg_full], check=True)
            console.print(f"[green][OK] Successfully created commit: {commit_msg_full}[/green]")
        except Exception as e:
            console.print(f"[red][ERROR] Git commit failed: {e}[/red]")

if __name__ == "__main__":
    app()
