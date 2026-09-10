"""Interactive handoff wizard — presentation layer.

Extracted from main.py to honor the <500-line rule.
"""
from __future__ import annotations

import datetime
import os
import typer
from rich.console import Console
from rich.panel import Panel

from aiorch.alerts import insert_alert, next_alert_id
from aiorch.config import load_config
from aiorch.context import generate_snapshot, inject_snapshot, update_context
from aiorch.decisions import append_decision
from aiorch.gitops import run_git_commit
from aiorch.logs import mark_session_recorded
from aiorch.models import AlertDraft, DecisionDraft

console = Console()


def run_handoff_wizard(with_snapshot: bool) -> None:
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
    # strip(): piped stdin on Windows leaves a trailing \r that would silently
    # fail the membership check and downgrade every answer to "feature".
    task_type = task_type.strip()
    if task_type not in valid_task_types:
        task_type = "feature"

    if models_config:
        recommended_model = models_config.get("recommendations", {}).get(task_type, models_config.get("default", "claude-sonnet-5"))
        reasoning_tasks = models_config.get("reasoning_tasks", [])
        # ASCII-only output: legacy Windows consoles (cp1252) crash Rich on
        # characters like U+2139/U+2713 — the [OK]/[WARN] prefix convention
        # exists for the same reason.
        console.print(f"\n[cyan][i] Recommended model: {recommended_model}[/cyan]")
        if task_type in reasoning_tasks:
            console.print("[yellow][OK] This task benefits from extended thinking mode[/yellow]")

    accomplishments = typer.prompt("What was accomplished in this block? (comma-separated, or empty to skip)", default="", show_default=False)
    changed_files = typer.prompt("What files or components were recently changed? (comma-separated, or empty to skip)", default="", show_default=False)

    add_alert = typer.confirm("Do you want to add a new blocker/alert?", default=False)
    new_alert_data: AlertDraft | None = None
    if add_alert:
        alerts_path = os.path.join(".ai", "ALERTS.md")
        alert_id = typer.prompt("Alert ID (leave blank to auto-assign)", default="")
        if not alert_id.strip():
            alert_id = next_alert_id(alerts_path)
        alert_title = typer.prompt("Short description")
        if not alert_title.strip():
            console.print("[yellow][WARN] Alert title is empty — skipping alert.[/yellow]")
        else:
            alert_severity = typer.prompt("Severity (P0 / P1 / P2)", default="P2")
            new_alert_data = {
                "id": alert_id.strip(),
                "title": alert_title.strip(),
                "severity": alert_severity.upper(),
            }

    add_decision = typer.confirm("Do you want to document a new design decision?", default=False)
    new_dec_data: DecisionDraft | None = None
    if add_decision:
        dec_id = typer.prompt("Decision ID (e.g. DEC-002)")
        dec_title = typer.prompt("Short title")
        if not dec_id.strip() or not dec_title.strip():
            console.print("[yellow][WARN] Decision ID or title is empty — skipping decision.[/yellow]")
        else:
            dec_context = typer.prompt("Decision context / rationale")
            new_dec_data = {"id": dec_id.strip(), "title": dec_title.strip(), "context": dec_context}

    make_commit = typer.confirm("Do you want to stage all changes and create a git commit?", default=False)
    commit_data = None
    if make_commit:
        block_num = typer.prompt("Block number (e.g. 3)")
        commit_type = typer.prompt("Commit type (feat/fix/chore/docs)")
        commit_msg = typer.prompt("Commit message description")
        commit_data = {"block": block_num, "type": commit_type, "msg": commit_msg}

    # --- PROCESS UPDATES (all prompts answered first, so a mid-wizard Ctrl+C
    # never leaves the .ai/ files half-written) ---
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    context_path = os.path.join(".ai", "CONTEXT.md")
    if update_context(context_path, today_str, accomplishments, changed_files):
        mark_session_recorded()
        console.print("[green][OK] Updated .ai/CONTEXT.md[/green]")

    if new_alert_data:
        alerts_path = os.path.join(".ai", "ALERTS.md")
        if insert_alert(alerts_path, new_alert_data, today_str):
            console.print(f"[green][OK] Added alert {new_alert_data['id']} to .ai/ALERTS.md[/green]")
        else:
            console.print(f"[yellow][WARN] Could not find severity section for {new_alert_data['severity']} in ALERTS.md[/yellow]")

    if new_dec_data:
        append_decision(os.path.join(".ai", "DECISIONS.md"), new_dec_data, today_str)
        console.print(f"[green][OK] Recorded decision {new_dec_data['id']} in .ai/DECISIONS.md[/green]")

    if commit_data:
        ok, detail = run_git_commit(commit_data["block"], commit_data["type"], commit_data["msg"])
        if ok:
            console.print(f"[green][OK] Successfully created commit: {detail}[/green]")
        else:
            console.print(f"[red][ERROR] {detail}[/red]")
            raise typer.Exit(1)

    if with_snapshot:
        snap = generate_snapshot("src")
        inject_snapshot(context_path, snap)
        console.print("[green][OK] Codebase snapshot injected into CONTEXT.md[/green]")
