import os
import shutil
import re
import datetime
import subprocess
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from aiorch._helpers import (parse_alerts, parse_lint_rules, check_staged_lint, update_section,
                             generate_snapshot, inject_snapshot, parse_pending, _next_action_id,
                             _insert_action, _resolve_action, _insert_alert, _next_alert_id,
                             load_config, update_context, append_decision, run_git_commit,
                             _has_merge_conflicts)

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

    pending = parse_pending(os.path.join(".ai", "PENDING.md"))
    if pending:
        pt = Table(title="Pending Manual Actions", header_style="bold cyan")
        pt.add_column("ID", style="dim", width=12)
        pt.add_column("Type")
        pt.add_column("Title")
        for a in pending:
            pt.add_row(a["id"], a["type"], a["title"])
        console.print(pt)

    console.print("\n[bold]Recommended Claude Models[/bold]")
    config_path = os.path.join(".ai", "config.json")
    config = load_config(config_path)
    if os.path.exists(config_path) and not config:
        console.print("[yellow][WARN] .ai/config.json is missing or corrupt — using defaults.[/yellow]")
    models_config = config.get("models", {}) if config else None

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
    # Fast path: use git grep (O(diff)) when inside a git repo; fall back to
    # file scan only when git is unavailable.
    if os.path.exists(".git") and _has_merge_conflicts():
        console.print("[red][ERROR] Merge conflicts detected in working tree.[/red]")
    elif not os.path.exists(".git"):
        # No git repo — do a file scan as fallback.
        conflict_found = False
        for root, dirs, files in os.walk("."):
            if any(ig in root for ig in [".git", "venv", ".venv", "node_modules", "__pycache__", ".pytest_cache"]):
                continue
            for file in files:
                if not file.endswith((".py", ".gd", ".go", ".js", ".ts", ".json", ".md", ".txt", ".html", ".xml", ".yml", ".yaml")):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    if re.search(r'^<{7}', content, re.MULTILINE) and re.search(r'^={7}$', content, re.MULTILINE):
                        console.print(f"[red][ERROR] Merge conflict found in {file_path}[/red]")
                        conflict_found = True
                except Exception:
                    pass
        if not conflict_found:
            console.print("[green][OK] No active merge conflicts detected.[/green]")
    else:
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

    test_cmd = config.get("test_command") if config else None
    if test_cmd:
        console.print(f"\n[bold]Running test command: {test_cmd}...[/bold]")
        try:
            test_res = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=30)
            if test_res.returncode == 0:
                console.print("[green][OK] Tests passed successfully![/green]")
            else:
                console.print(f"[red][ERROR] Test command failed with exit code {test_res.returncode}[/red]")
                if test_res.stdout:
                    console.print(test_res.stdout)
                if test_res.stderr:
                    console.print(test_res.stderr)
        except subprocess.TimeoutExpired:
            console.print("[yellow][WARN] Test command timed out after 30 seconds.[/yellow]")
        except Exception as e:
            console.print(f"[yellow][WARN] Could not run test command. Reason: {e}[/yellow]")

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

    post_hook_path = os.path.join(hook_dir, "post-commit")
    post_hook_content = """#!/bin/sh
# AI Orchestrator post-commit: keep codebase snapshot fresh

if command -v ai-orch >/dev/null 2>&1; then
  ai-orch snapshot --quiet 2>/dev/null || true
else
  python -m aiorch.main snapshot --quiet 2>/dev/null || true
fi
"""
    with open(post_hook_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(post_hook_content)
    try:
        os.chmod(post_hook_path, 0o755)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not set executable permission on post-commit hook. Reason: {e}[/yellow]")
    console.print(f"[green][OK] Git post-commit hook installed at {post_hook_path}[/green]")

@app.command()
def handoff(
    with_snapshot: bool = typer.Option(False, "--snapshot", help="Append codebase symbol snapshot to CONTEXT.md"),
):
    """Run interactive handoff wizard to update .ai documentation and commit changes."""
    if not os.path.exists(".ai"):
        console.print("[red]Error: .ai/ orchestrator folder not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)
        
    console.print(Panel("[bold green]AI Orchestrator — Session Handoff Wizard[/bold green]", expand=False))

    config_path = os.path.join(".ai", "config.json")
    config = load_config(config_path)
    if os.path.exists(config_path) and not config:
        console.print("[yellow][WARN] .ai/config.json is missing or corrupt — model recommendations unavailable.[/yellow]")
    models_config = config.get("models", {}) if config else None

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
        alerts_path = os.path.join(".ai", "ALERTS.md")
        alert_id = typer.prompt("Alert ID (leave blank to auto-assign)", default="")
        if not alert_id.strip():
            alert_id = _next_alert_id(alerts_path)
        alert_title = typer.prompt("Short description")
        if not alert_title.strip():
            console.print("[yellow][WARN] Alert title is empty — skipping alert.[/yellow]")
        else:
            alert_severity = typer.prompt("Severity (P0 / P1 / P2)", default="P2")
            new_alert_data = {
                "id": alert_id.strip(),
                "title": alert_title.strip(),
                "severity": alert_severity.upper()
            }

    add_decision = typer.confirm("Do you want to document a new design decision?", default=False)
    new_dec_data = None
    if add_decision:
        dec_id = typer.prompt("Decision ID (e.g. DEC-002)")
        dec_title = typer.prompt("Short title")
        if not dec_id.strip() or not dec_title.strip():
            console.print("[yellow][WARN] Decision ID or title is empty — skipping decision.[/yellow]")
        else:
            dec_context = typer.prompt("Decision context / rationale")
            new_dec_data = {
                "id": dec_id.strip(),
                "title": dec_title.strip(),
                "context": dec_context,
            }

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

    context_path = os.path.join(".ai", "CONTEXT.md")
    if update_context(context_path, today_str, accomplishments, changed_files):
        console.print("[green][OK] Updated .ai/CONTEXT.md[/green]")

    if new_alert_data:
        alerts_path = os.path.join(".ai", "ALERTS.md")
        if _insert_alert(alerts_path, new_alert_data, today_str):
            console.print(f"[green][OK] Added alert {new_alert_data['id']} to .ai/ALERTS.md[/green]")
        else:
            console.print(f"[yellow][WARN] Could not find severity section for {new_alert_data['severity']} in ALERTS.md[/yellow]")

    if new_dec_data:
        decisions_path = os.path.join(".ai", "DECISIONS.md")
        append_decision(decisions_path, new_dec_data, today_str)
        console.print(f"[green][OK] Recorded decision {new_dec_data['id']} in .ai/DECISIONS.md[/green]")

    if commit_data:
        ok, detail = run_git_commit(commit_data["block"], commit_data["type"], commit_data["msg"])
        if ok:
            console.print(f"[green][OK] Successfully created commit: {detail}[/green]")
        else:
            console.print(f"[red][ERROR] {detail}[/red]")
            raise typer.Exit(1)

    if with_snapshot:
        context_path = os.path.join(".ai", "CONTEXT.md")
        snap = generate_snapshot("src")
        inject_snapshot(context_path, snap)
        console.print("[green][OK] Codebase snapshot injected into CONTEXT.md[/green]")

@app.command()
def snapshot(
    src: str = typer.Option("src", "--src", help="Source directory to scan (default: src/)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output (used by post-commit hook)"),
):
    """Scan codebase and inject a symbol snapshot into .ai/CONTEXT.md."""
    if not os.path.exists(".ai"):
        if not quiet:
            console.print("[red]Error: .ai/ not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)
    snap = generate_snapshot(src)
    inject_snapshot(os.path.join(".ai", "CONTEXT.md"), snap)
    if not quiet:
        console.print("[green][OK] Codebase snapshot injected into CONTEXT.md[/green]")

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


@app.command("action-add")
def action_add(
    title: str = typer.Argument(..., help="Short description of the action"),
    action_type: str = typer.Option("other", "--type", "-t", help="Type: db | infra | other"),
    target: str = typer.Option("[TBD]", "--target", help="Where to perform the action"),
    sql: str = typer.Option("", "--sql", help="SQL to run (for db actions)"),
    steps: str = typer.Option("", "--steps", help="Manual steps description"),
):
    """Add a pending manual action to .ai/PENDING.md."""
    if not title.strip():
        console.print("[red]Error: title cannot be empty.[/red]")
        raise typer.Exit(1)
    pending_path = os.path.join(".ai", "PENDING.md")
    if not os.path.exists(pending_path):
        tmpl = os.path.join(os.path.dirname(__file__), "templates", "PENDING.md")
        shutil.copy(tmpl, pending_path)
    prefix = {"db": "DB", "infra": "INFRA"}.get(action_type.lower(), "ACTION")
    action_id = _next_action_id(pending_path, prefix)
    today = datetime.date.today().strftime("%Y-%m-%d")
    data = {"id": action_id, "title": title, "type": action_type, "target": target,
            "sql": sql or None, "steps": steps or None}
    if _insert_action(pending_path, data, today):
        console.print(f"[green][OK] Added {action_id}: {title}[/green]")
    else:
        console.print(f"[red]Error: Section for type '{action_type}' not found[/red]")
        raise typer.Exit(1)


@app.command("action-resolve")
def action_resolve(action_id: str = typer.Argument(..., help="Action ID to mark as done (e.g. DB-001)")):
    """Mark a pending action as done and move it to DONE."""
    if not action_id.strip():
        console.print("[red]Error: action_id cannot be empty.[/red]")
        raise typer.Exit(1)
    pending_path = os.path.join(".ai", "PENDING.md")
    if not os.path.exists(pending_path):
        console.print("[red]Error: .ai/PENDING.md not found.[/red]")
        raise typer.Exit(1)
    if _resolve_action(pending_path, action_id):
        console.print(f"[green][OK] {action_id} marked as Done[/green]")
    else:
        console.print(f"[red]Error: {action_id} not found in PENDING.md[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
