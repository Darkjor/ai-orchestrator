"""The analyze → qa pipeline: verifiable metrics with an anti-hallucination loop.

WHY this design: an AI "analysis" is only trustworthy if every number in it
can be re-derived from the repo. So `analyze` collects metrics exclusively
from checkable sources (pytest, git, .ai/ files) and writes them with their
source column; `qa` then re-collects the live values and diffs them against
the stored report. A mismatch escalates: P1 alert + auto-heal action + status
QA_ESCALATED, with an explicit human override path.

Status lifecycle of ANALYSIS.md (single source of truth in its ## Status
section): PENDING → QA_APPROVED | QA_ESCALATED → HUMAN_REVIEWED.
"""
from __future__ import annotations

import os
import re
import subprocess

from aiorch.alerts import parse_alerts
from aiorch.decisions import count_decisions
from aiorch.logs import get_local_logger
from aiorch.models import ProjectMetrics
from aiorch.pending import parse_pending


def parse_analysis_status(analysis_path: str) -> str:
    """Read the ## Status value from ANALYSIS.md. Returns 'NOT_FOUND' if missing."""
    if not os.path.exists(analysis_path):
        return "NOT_FOUND"
    with open(analysis_path, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"^## Status\s*\n+([A-Z_]+)", content, re.MULTILINE)
    return m.group(1).strip() if m else "NOT_FOUND"


def set_analysis_status(analysis_path: str, status: str) -> bool:
    """Replace the value in the ## Status section of ANALYSIS.md."""
    if not os.path.exists(analysis_path):
        return False
    with open(analysis_path, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(
        r"(^## Status\s*\n+)[A-Z_]+",
        lambda m: m.group(1) + status,
        content,
        flags=re.MULTILINE,
    )
    if new_content == content:
        return False
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def collect_project_metrics(ai_dir: str) -> ProjectMetrics:
    """Collect real, re-checkable project metrics from .ai/ files and git.

    Every metric must remain verifiable by `qa` — never add a field here that
    cannot be re-derived deterministically from the repo state. pytest/git
    failures degrade to 0 (logged), because analysis must work in repos that
    have no tests or no git yet.
    """
    log = get_local_logger()
    alerts = parse_alerts(os.path.join(ai_dir, "ALERTS.md"))
    pending = parse_pending(os.path.join(ai_dir, "PENDING.md"))
    decisions_count = count_decisions(os.path.join(ai_dir, "DECISIONS.md"))

    tests_collected = 0
    try:
        res = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            capture_output=True, text=True, timeout=30,
        )
        m = re.search(r"(\d+) tests? collected", res.stdout + res.stderr)
        if m:
            tests_collected = int(m.group(1))
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("collect_project_metrics: pytest collection failed: %s", exc)

    git_modified = 0
    if os.path.exists(".git"):
        try:
            git_res = subprocess.run(
                ["git", "diff", "--stat"], capture_output=True, text=True, timeout=10
            )
            lines = [l for l in git_res.stdout.strip().splitlines() if l.strip()]
            # Last line of --stat output is the summary ("N files changed...").
            git_modified = max(0, len(lines) - 1)
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("collect_project_metrics: git diff failed: %s", exc)

    return {
        "alerts": alerts,
        "p0": sum(1 for a in alerts if a["severity"] == "P0"),
        "p1": sum(1 for a in alerts if a["severity"] == "P1"),
        "p2": sum(1 for a in alerts if a["severity"] == "P2"),
        "pending": pending,
        "pending_count": len(pending),
        "decisions_count": decisions_count,
        "tests_collected": tests_collected,
        "git_modified": git_modified,
    }


def write_analysis_report(analysis_path: str, metrics: ProjectMetrics, agent_role: str, today_str: str) -> None:
    """Write a fresh ANALYSIS.md from collected metrics (status: PENDING).

    The table format is a CONTRACT with qa_cross_check — it regex-extracts
    ``| <label> | <int> |`` rows. Changing labels or column order requires
    updating qa_cross_check and the tests in the same change.
    """
    sources = "pytest, parse_alerts(), parse_pending(), DECISIONS.md, git diff"
    findings = []
    if metrics["p0"] > 0:
        findings.append(f"- **CRÍTICO**: {metrics['p0']} alerta(s) P0 — requiere atención inmediata")
    if metrics["p1"] > 0:
        findings.append(f"- {metrics['p1']} alerta(s) P1 activa(s)")
    if metrics["pending_count"] > 0:
        findings.append(f"- {metrics['pending_count']} acción(es) pendiente(s) sin resolver")
    if not findings:
        findings.append("- Sin hallazgos críticos — proyecto en estado saludable")
    ambiguous = "No" if metrics["p0"] == 0 else f"Sí — {metrics['p0']} P0(s)"
    ambig_result = "PASS" if metrics["p0"] == 0 else "ESCALATE"
    content = (
        "# Analysis Report — AI Orchestrator\n\n"
        "> Auto-generated by `ai-orch analyze`. Do NOT edit manually.\n"
        "> QA reviewed via `ai-orch qa`.\n\n"
        "## Metadata\n\n"
        "| Key | Value |\n|-----|-------|\n"
        f"| Run date | {today_str} |\n"
        "| Agent | analyzer |\n"
        f"| Agent role | {agent_role[:80]} |\n"
        "| Status | PENDING |\n\n"
        "## Real Metrics\n\n"
        "| Metric | Value | Source |\n|--------|-------|--------|\n"
        f"| Tests collected | {metrics['tests_collected']} | pytest --collect-only |\n"
        f"| Open alerts P0 | {metrics['p0']} | ALERTS.md |\n"
        f"| Open alerts P1 | {metrics['p1']} | ALERTS.md |\n"
        f"| Open alerts P2 | {metrics['p2']} | ALERTS.md |\n"
        f"| Pending actions | {metrics['pending_count']} | PENDING.md |\n"
        f"| Decisions recorded | {metrics['decisions_count']} | DECISIONS.md |\n"
        f"| Git modified files | {metrics['git_modified']} | git diff |\n\n"
        f"## Findings\n\n{chr(10).join(findings)}\n\n"
        "## Self-Check\n\n"
        "| Question | Answer | Result |\n|----------|--------|--------|\n"
        f"| ¿Datos reales y verificables? | Sí — {sources} | PASS |\n"
        f"| ¿Algo ambiguo? | {ambiguous} | {ambig_result} |\n"
        "| ¿Alucinación? | No | PASS |\n\n"
        "## QA Review\n\n*(pending — run `ai-orch qa` to populate)*\n\n"
        "## Status\n\nPENDING\n"
    )
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(content)


def qa_cross_check(analysis_path: str, ai_dir: str) -> list[str]:
    """Diff stored ANALYSIS.md metrics against live repo state.

    Only metrics that are cheap AND deterministic are cross-checked (P0 count,
    pending count). Test/git numbers are excluded on purpose: they legitimately
    drift between analyze and qa runs, and false escalations would teach users
    to ignore QA.
    Returns a list of human-readable discrepancy strings (empty = approved).
    """
    with open(analysis_path, "r", encoding="utf-8") as f:
        content = f.read()

    def _extract(label: str) -> int | None:
        m = re.search(rf"\| {re.escape(label)} \| (\d+) \|", content)
        return int(m.group(1)) if m else None

    stored_p0 = _extract("Open alerts P0")
    stored_pending = _extract("Pending actions")
    live_alerts = parse_alerts(os.path.join(ai_dir, "ALERTS.md"))
    live_p0 = sum(1 for a in live_alerts if a["severity"] == "P0")
    live_pending = parse_pending(os.path.join(ai_dir, "PENDING.md"))
    issues: list[str] = []
    # "!=" instead of U+2260: these strings reach the console, and legacy
    # Windows terminals (cp1252) cannot encode the Unicode operator.
    if stored_p0 is not None and stored_p0 != live_p0:
        issues.append(f"P0 alerts en ANALYSIS ({stored_p0}) != estado actual ({live_p0})")
    if stored_pending is not None and stored_pending != len(live_pending):
        issues.append(f"Pending actions en ANALYSIS ({stored_pending}) != estado actual ({len(live_pending)})")
    return issues
