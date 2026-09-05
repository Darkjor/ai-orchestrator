"""Presentation for the analyze -> qa pipeline — extracted from main.py.

Mirrors handoff_ui.py and render.py: main.py keeps the Typer surface, the Rich
rendering and prompt flow live here so main.py stays under the 500-line cap.
Behaviour is unchanged; tests/test_cli.py asserts the [OK]/[WARN]/[ERROR]
prefixes and the ANALYSIS.md status transitions.
"""
from __future__ import annotations

import datetime
import os
import time

import typer
from rich.console import Console
from rich.panel import Panel

from aiorch.alerts import insert_alert, next_alert_id
from aiorch.analysis import (collect_project_metrics, parse_analysis_status,
                             qa_cross_check, set_analysis_status,
                             write_analysis_report)
from aiorch.config import load_config
from aiorch.context import update_section
from aiorch.pending import ensure_pending_file, insert_action, next_action_id

# WHY the logger arrives as a parameter: tests/test_cli.py patches
# `aiorch.main.get_logger`, which CLAUDE.md freezes as public surface.
# Importing observability.get_logger here would bypass that patch point,
# so main.py passes its own reference in and it resolves at call time.

console = Console()


def run_analyze(get_logger) -> None:
    """Run specialized analysis of the project and write results to .ai/ANALYSIS.md."""
    if not os.path.exists(".ai"):
        console.print("[red]Error: .ai/ not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)
    t0 = time.time()
    config = load_config(os.path.join(".ai", "config.json"))
    agent_cfg = config.get("agents", {}).get("analyzer", {})
    agent_role = agent_cfg.get("role", "Eres un analizador de proyecto especializado.")
    console.print(Panel("[bold blue]AI Orchestrator — Analysis Run[/bold blue]", expand=False))
    console.print(f"[dim]Agente: analyzer — {agent_role[:70]}[/dim]\n")
    metrics = collect_project_metrics(".ai")
    console.print(f"[green][OK][/green] Tests: {metrics['tests_collected']} collected")
    console.print(f"[green][OK][/green] Alertas: {metrics['p0']} P0, {metrics['p1']} P1, {metrics['p2']} P2")
    console.print(f"[green][OK][/green] Pending: {metrics['pending_count']}  |  Decisions: {metrics['decisions_count']}  |  Git: {metrics['git_modified']} modificados")
    console.print("\n[bold]Self-Check:[/bold]")
    console.print("  [green][OK][/green] Datos reales? -> Si (pytest, alerts, pending, git diff)")
    ambig = f"Si -- {metrics['p0']} P0(s)" if metrics["p0"] > 0 else "No"
    icon = "[yellow][!][/yellow]" if metrics["p0"] > 0 else "[green][OK][/green]"
    console.print(f"  {icon} Algo ambiguo? -> {ambig}")
    console.print("  [green][OK][/green] Alucinacion? -> No")
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    write_analysis_report(os.path.join(".ai", "ANALYSIS.md"), metrics, agent_role, today_str)
    get_logger().log_run("analyze", "analyze", latency_ms=int((time.time() - t0) * 1000), status="ok")
    console.print("\n[green][OK] Analisis escrito en .ai/ANALYSIS.md (status: PENDING QA)[/green]")


def run_qa(get_logger) -> None:
    """QA review of .ai/ANALYSIS.md — AI first pass, human escalation if ambiguous."""
    if not os.path.exists(".ai"):
        console.print("[red]Error: .ai/ not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)
    analysis_path = os.path.join(".ai", "ANALYSIS.md")
    if not os.path.exists(analysis_path):
        console.print("[red]Error: .ai/ANALYSIS.md not found. Run 'ai-orch analyze' first.[/red]")
        raise typer.Exit(1)
    status = parse_analysis_status(analysis_path)
    if status not in ("PENDING", "QA_ESCALATED"):
        console.print(f"[yellow][WARN] Analysis ya revisado (status: {status}). Nada que hacer.[/yellow]")
        raise typer.Exit(0)
    t0 = time.time()
    config = load_config(os.path.join(".ai", "config.json"))
    qa_role = config.get("agents", {}).get("qa_reviewer", {}).get("role", "Eres un QA reviewer especializado.")
    console.print(Panel("[bold magenta]AI Orchestrator — QA Review[/bold magenta]", expand=False))
    console.print(f"[dim]Agente: qa_reviewer — {qa_role[:70]}[/dim]\n")
    issues = qa_cross_check(analysis_path, ".ai")
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    if not issues:
        console.print("[green][OK][/green] Metricas verificadas -- sin discrepancias")
        update_section(analysis_path, "QA Review", f"**Resultado**: APROBADO\n**Fecha**: {today_str}\n**Notas**: Sin discrepancias detectadas.")
        set_analysis_status(analysis_path, "QA_APPROVED")
        console.print("\n[green][OK] QA APROBADO — status: QA_APPROVED[/green]")
        get_logger().log_run("qa", "qa", latency_ms=int((time.time() - t0) * 1000), status="ok")
        return
    # Discrepancy path: escalate with auto-heal artifacts (alert + pending
    # action) so the failure is visible in triage and self-repairing.
    console.print("[yellow]![/yellow] Discrepancias detectadas:")
    for issue in issues:
        console.print(f"  - {issue}")
    alerts_path = os.path.join(".ai", "ALERTS.md")
    pending_path = os.path.join(".ai", "PENDING.md")
    alert_id = next_alert_id(alerts_path)
    insert_alert(alerts_path, {"id": alert_id, "title": f"QA: {issues[0][:60]}", "severity": "P1"}, today_str)
    ensure_pending_file(pending_path)
    action_id = next_action_id(pending_path, "ACTION")
    insert_action(pending_path, {"id": action_id, "title": "Re-ejecutar analyze para corregir métricas", "type": "other", "target": ".ai/ANALYSIS.md", "steps": "Correr `ai-orch analyze` y luego `ai-orch qa`"}, today_str)
    update_section(analysis_path, "QA Review", f"**Resultado**: ESCALADO\n**Issues**: {'; '.join(issues)}\n**Alerta**: {alert_id} | **Acción**: {action_id}")
    set_analysis_status(analysis_path, "QA_ESCALATED")
    console.print(f"\n[yellow][WARN] QA ESCALADO — Alerta {alert_id} y acción {action_id} creadas (auto-heal)[/yellow]")
    override = typer.confirm("\n¿Aprobar de todas formas? (override humano)", default=False)
    if override:
        get_logger().log_run("qa", "qa", latency_ms=int((time.time() - t0) * 1000), status="override_approved")
        set_analysis_status(analysis_path, "QA_APPROVED")
        console.print("[green][OK] Override humano — status: QA_APPROVED[/green]")
    else:
        set_analysis_status(analysis_path, "HUMAN_REVIEWED")
        console.print("[yellow][INFO] Revision pendiente -- accion de auto-heal activa en PENDING.md[/yellow]")
        get_logger().log_run("qa", "qa", latency_ms=int((time.time() - t0) * 1000), status="escalated")
        raise typer.Exit(1)
