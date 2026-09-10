"""Shared Rich rendering for the CLI — extracted from main.py.

Mirrors handoff_ui.py: main.py holds the Typer surface, the Rich rendering
that would push it past the 500-line cap lives here. Behaviour is unchanged;
the [OK]/[WARN]/[ERROR] output contract is asserted by tests/test_cli.py.
"""
from __future__ import annotations

import subprocess

from rich.console import Console
from rich.table import Table

console = Console()


def _print_model_recommendations(config: dict) -> None:
    """Render the model-routing block shared by triage output."""
    console.print("\n[bold]Recommended Claude Models[/bold]")
    models_config = config.get("models", {}) if config else None
    if not models_config:
        console.print("[dim]No model recommendations configured in .ai/config.json[/dim]")
        return
    default_model = models_config.get("default", "claude-sonnet-5")
    recommendations = models_config.get("recommendations", {})
    reasoning_tasks = models_config.get("reasoning_tasks", [])
    console.print(f"Default: [cyan]{default_model}[/cyan]")
    for task_type, model in recommendations.items():
        reasoning_note = " (with extended thinking)" if task_type in reasoning_tasks else ""
        console.print(f"  {task_type}: [yellow]{model}{reasoning_note}[/yellow]")


def _run_configured_tests(test_cmd: str) -> None:
    """Run the project's configured test command and report the outcome."""
    console.print(f"\n[bold]Running test command: {test_cmd}...[/bold]")
    try:
        # shell=True is intentional: test_command comes from the project's own
        # config.json (trusted, same trust level as a Makefile).
        res = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        console.print("[yellow][WARN] Test command timed out after 30 seconds.[/yellow]")
        return
    except OSError as e:
        console.print(f"[yellow][WARN] Could not run test command. Reason: {e}[/yellow]")
        return
    if res.returncode == 0:
        console.print("[green][OK] Tests passed successfully![/green]")
        return
    console.print(f"[red][ERROR] Test command failed with exit code {res.returncode}[/red]")
    if res.stdout:
        console.print(res.stdout)
    if res.stderr:
        console.print(res.stderr)


def render_runs_table(runs: list) -> Table:
    """Build the Rich table for `ai-orch observe` from Supabase rows."""
    table = Table(title=f"Recent Agent Runs (last {len(runs)})", header_style="bold cyan")
    for col, justify in (("agent_id", "left"), ("command", "left"), ("timestamp", "left"),
                         ("latency_ms", "right"), ("cost_usd", "right"),
                         ("status", "left"), ("eval_score", "right")):
        table.add_column(col, justify=justify)
    for row in runs:
        table.add_row(
            str(row.get("agent_id", "")),
            str(row.get("command", "")),
            str(row.get("timestamp", ""))[:19],
            str(row.get("latency_ms", "")),
            str(row.get("cost_usd", "")),
            str(row.get("status", "")),
            str(row.get("eval_score") or ""),
        )
    return table


def render_roles_table(versions: list) -> Table:
    """Build the Rich table for `ai-orch roles` from (role, version) pairs."""
    table = Table(title="Agent role prompts", header_style="bold cyan")
    table.add_column("Role")
    table.add_column("Prompt version")
    for name, version in versions:
        style = "yellow" if version == "unversioned" else "green"
        table.add_row(name, f"[{style}]{version}[/{style}]")
    return table
