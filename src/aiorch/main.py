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
from aiorch._helpers import parse_alerts, parse_lint_rules, check_staged_lint, update_section

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
    
    if not os.path.exists(template_dir):
        console.print(f"[red]Error: Templates directory {template_dir} not found.[/red]")
        raise typer.Exit(1)
        
    for filename in os.listdir(template_dir):
        src = os.path.join(template_dir, filename)
        dst = os.path.join(".ai", filename)
        shutil.copy(src, dst)
    
    console.print("[green]Successfully initialized .ai/ orchestrator folder![/green]")

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
        if f.startswith(".ai/"):
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

    wheels_path = os.path.join(".ai", "WHEELS.md")
    rules = parse_lint_rules(wheels_path)
    if rules:
        violations = check_staged_lint(staged_files, rules)
        if violations:
            console.print(Panel("[red]WHEELS.md Lint Violations — commit blocked[/red]", expand=False))
            for v in violations:
                console.print(f"[red]✗[/red] [bold]{v['file']}:{v['line']}[/bold] — {v['message']}")
                console.print(f"  [dim]{v['code']}[/dim]")
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

@app.command()
def update(
    section: str = typer.Option(..., "--section", "-s", help="Section heading to update"),
    value: str = typer.Option(..., "--value", "-v", help="New content for the section (use \\n for newlines)"),
    file: str = typer.Option("CONTEXT.md", "--file", "-f", help=".ai/ file to update"),
):
    """Non-interactively update a section in a .ai/ file (for agent use)."""
    if not os.path.exists(".ai"):
        console.print("[red]Error: .ai/ not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)
    filepath = os.path.join(".ai", file)
    if update_section(filepath, section, value):
        console.print(f"[green][OK] Updated '{section}' in {file}[/green]")
    else:
        console.print(f"[red]Error: Section '{section}' not found in {filepath}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
