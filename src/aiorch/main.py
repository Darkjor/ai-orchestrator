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


def _next_alert_id(alerts_path: str) -> str:
    """Return the next sequential alert ID based on existing alerts in the file."""
    existing = parse_alerts(alerts_path)
    if not existing:
        return "ALERT-001"
    numbers = [int(re.search(r"\d+", a["id"]).group()) for a in existing if re.search(r"\d+", a["id"])]
    return f"ALERT-{(max(numbers) + 1):03d}"


def _insert_alert(alerts_path: str, alert_data: dict, today_str: str) -> bool:
    """Insert a formatted alert block under the matching severity section. Returns True on success."""
    with open(alerts_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    header_pattern = f"## {alert_data['severity']}"
    for i, line in enumerate(lines):
        if header_pattern in line:
            alert_md = (
                f"\n### [{alert_data['id']}] {alert_data['title']}\n"
                f"**Severity**: {alert_data['severity']}\n"
                f"**Status**:   Open\n"
                f"**Owner**:    None\n"
                f"**Discovered**: {today_str}\n"
                f"**Impact**: [TBD]\n"
                f"**Fix**: [TBD]\n"
            )
            lines.insert(i + 1, alert_md)
            with open(alerts_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
    return False


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

    accomplishments = typer.prompt("What was accomplished in this block? (comma-separated, or empty to skip)", default="", show_default=False)
    changed_files = typer.prompt("What files or components were recently changed? (comma-separated, or empty to skip)", default="", show_default=False)

    add_alert = typer.confirm("Do you want to add a new blocker/alert?", default=False)
    new_alert_data = None
    if add_alert:
        alert_id = typer.prompt("Alert ID (e.g. ALERT-002)")
        alert_title = typer.prompt("Short description")
        alert_severity = typer.prompt("Severity (P0 / P1 / P2)", default="P2")
        new_alert_data = {"id": alert_id, "title": alert_title, "severity": alert_severity.upper()}

    add_decision = typer.confirm("Do you want to document a new design decision?", default=False)
    new_dec_data = None
    if add_decision:
        dec_id = typer.prompt("Decision ID (e.g. DEC-002)")
        dec_title = typer.prompt("Short title")
        dec_context = typer.prompt("Decision context / rationale")
        new_dec_data = {"id": dec_id, "title": dec_title, "context": dec_context}

    make_commit = typer.confirm("Do you want to stage all changes and create a git commit?", default=False)
    commit_data = None
    if make_commit:
        block_num = typer.prompt("Block number (e.g. 3)")
        commit_type = typer.prompt("Commit type (feat/fix/chore/docs)")
        commit_msg = typer.prompt("Commit message description")
        commit_data = {"block": block_num, "type": commit_type, "msg": commit_msg}

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    context_path = os.path.join(".ai", "CONTEXT.md")
    if os.path.exists(context_path):
        with open(context_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"## Current State \(updated: [^\)]+\)", f"## Current State (updated: {today_str})", content)
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
                    next_sec_idx = next((j for j in range(i+1, len(lines)) if lines[j].strip().startswith("---") or lines[j].strip().startswith("##")), len(lines))
                    lines = lines[:i+1] + new_bullets + lines[next_sec_idx:]
                    break
            content = "\n".join(lines)
        with open(context_path, "w", encoding="utf-8") as f:
            f.write(content)
        console.print("[green][OK] Updated .ai/CONTEXT.md[/green]")

    if new_alert_data:
        alerts_path = os.path.join(".ai", "ALERTS.md")
        if os.path.exists(alerts_path) and _insert_alert(alerts_path, new_alert_data, today_str):
            console.print(f"[green][OK] Added alert {new_alert_data['id']} to .ai/ALERTS.md[/green]")

    if new_dec_data:
        decisions_path = os.path.join(".ai", "DECISIONS.md")
        if os.path.exists(decisions_path):
            decision_md = (
                f"\n## [{new_dec_data['id']}] {new_dec_data['title']}\n"
                f"**Date**: {today_str}\n**Status**: Active\n"
                f"**Context**: {new_dec_data['context']}\n"
                f"**Decision**: [TBD]\n**Rationale**: [TBD]\n**Consequences**: [TBD]\n**Revisit when**: [TBD]\n"
            )
            with open(decisions_path, "a", encoding="utf-8") as f:
                f.write(decision_md)
            console.print(f"[green][OK] Recorded decision {new_dec_data['id']} in .ai/DECISIONS.md[/green]")

    if commit_data:
        try:
            subprocess.run(["git", "add", "."], check=True)
            commit_msg_full = f"[{commit_data['block']}] {commit_data['type']}: {commit_data['msg']}"
            subprocess.run(["git", "commit", "-m", commit_msg_full], check=True)
            console.print(f"[green][OK] Successfully created commit: {commit_msg_full}[/green]")
        except Exception as e:
            console.print(f"[red][ERROR] Git commit failed: {e}[/red]")

@app.command("alert-add")
def alert_add(
    title: str = typer.Argument(..., help="Short description of the alert"),
    severity: str = typer.Option("P2", "--severity", "-s", help="Severity level: P0, P1, or P2"),
    alert_id: str = typer.Option(None, "--id", help="Alert ID (e.g. ALERT-003). Auto-generated if omitted."),
):
    """Add a new alert to .ai/ALERTS.md atomically."""
    severity = severity.upper()
    if severity not in ("P0", "P1", "P2"):
        console.print(f"[red]Error: Invalid severity '{severity}'. Must be P0, P1, or P2.[/red]")
        raise typer.Exit(1)

    alerts_path = os.path.join(".ai", "ALERTS.md")
    if not os.path.exists(alerts_path):
        console.print("[red]Error: .ai/ALERTS.md not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)

    resolved_id = alert_id or _next_alert_id(alerts_path)

    with open(alerts_path, "r", encoding="utf-8") as f:
        content = f.read()
    if f"[{resolved_id}]" in content:
        console.print(f"[red]Error: Alert ID '{resolved_id}' already exists in ALERTS.md.[/red]")
        raise typer.Exit(1)

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    alert_data = {"id": resolved_id, "title": title, "severity": severity}
    if _insert_alert(alerts_path, alert_data, today_str):
        console.print(f"[green][OK] Added [{resolved_id}] ({severity}): {title}[/green]")
    else:
        console.print(f"[red]Error: Could not find '## {severity}' section in ALERTS.md.[/red]")
        raise typer.Exit(1)


@app.command("alert-resolve")
def alert_resolve(
    alert_id: str = typer.Argument(..., help="Alert ID to resolve (e.g. ALERT-001)"),
):
    """Move an alert to the RESOLVED section of .ai/ALERTS.md."""
    alerts_path = os.path.join(".ai", "ALERTS.md")
    if not os.path.exists(alerts_path):
        console.print("[red]Error: .ai/ALERTS.md not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)
    with open(alerts_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start_idx = next(
        (i for i, l in enumerate(lines) if re.search(rf"### \[{re.escape(alert_id)}\]", l)),
        None
    )
    if start_idx is None:
        console.print(f"[red]Error: Alert '{alert_id}' not found in ALERTS.md.[/red]")
        raise typer.Exit(1)
    end_idx = next(
        (i for i in range(start_idx + 1, len(lines)) if lines[i].startswith("###") or lines[i].startswith("## ")),
        len(lines)
    )
    block = [re.sub(r"\*\*Status\*\*:\s+Open", "**Status**:   Resolved", l) for l in lines[start_idx:end_idx]]
    remaining = lines[:start_idx] + lines[end_idx:]
    resolved_idx = next((i for i, l in enumerate(remaining) if l.startswith("## RESOLVED")), None)
    if resolved_idx is None:
        console.print("[red]Error: '## RESOLVED' section not found in ALERTS.md.[/red]")
        raise typer.Exit(1)
    with open(alerts_path, "w", encoding="utf-8") as f:
        f.writelines(remaining[:resolved_idx + 1] + ["\n"] + block + remaining[resolved_idx + 1:])
    console.print(f"[green][OK] Alert '{alert_id}' marked as Resolved and moved to RESOLVED section.[/green]")


if __name__ == "__main__":
    app()
