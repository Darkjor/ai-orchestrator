"""Parsing and mutation of .ai/ALERTS.md — the P0/P1/P2 issue tracker.

WHY Markdown instead of a database: the .ai/ folder is shared memory between
*any* AI model and humans. Markdown is the one format every LLM reads and
patches reliably without drivers or schemas, and it diffs cleanly in git.

Format contract (changing it requires updating templates/ALERTS.md and the
tests in tests/test_cli.py):
- Severity comes from the ``## P0`` / ``## P1`` / ``## P2`` section an alert
  sits under — it is positional, not declared per alert.
- Alerts under ``## RESOLVED`` are invisible to parse_alerts but still count
  for next_alert_id, so IDs are never reused after resolution.
- Alert headers look like ``### [ALERT-001] Title``.
"""
from __future__ import annotations

import os
import re

from aiorch.logs import get_local_logger
from aiorch.models import Alert, AlertDraft

# Module-level compiled regexes — avoids per-call re.compile() overhead.
_RE_ALERT_HEADER = re.compile(r"### \[(ALERT-\d+)\]\s*(.*)")
_RE_ALERT_ID = re.compile(r"### \[(ALERT-(\d+))\]")


def parse_alerts(alerts_path: str) -> list[Alert]:
    """Return open P0/P1/P2 alerts from ALERTS.md (RESOLVED section excluded)."""
    if not os.path.exists(alerts_path):
        return []
    alerts: list[Alert] = []
    current_severity = "P2"
    with open(alerts_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        s = line.strip()
        if s.startswith("## P0"):
            current_severity = "P0"
        elif s.startswith("## P1"):
            current_severity = "P1"
        elif s.startswith("## P2"):
            current_severity = "P2"
        elif s.startswith("## RESOLVED"):
            current_severity = "RESOLVED"
        if s.startswith("### [ALERT-"):
            m = _RE_ALERT_HEADER.search(s)
            if m and current_severity != "RESOLVED":
                alerts.append(
                    {"id": m.group(1), "title": m.group(2), "severity": current_severity, "status": "Open"}
                )
    return alerts


def all_alert_ids(alerts_path: str) -> list[int]:
    """Return every numeric ALERT ID, including resolved ones.

    Resolved alerts must count: reusing an ID after resolution would corrupt
    cross-references in DECISIONS.md / commit messages that mention old IDs.
    """
    if not os.path.exists(alerts_path):
        return []
    ids: list[int] = []
    with open(alerts_path, "r", encoding="utf-8") as f:
        for line in f:
            m = _RE_ALERT_ID.search(line)
            if m:
                ids.append(int(m.group(2)))
    return ids


def next_alert_id(alerts_path: str) -> str:
    """Return the next sequential ALERT-XXX ID."""
    numbers = all_alert_ids(alerts_path)
    if not numbers:
        return "ALERT-001"
    return f"ALERT-{(max(numbers) + 1):03d}"


def insert_alert(alerts_path: str, alert_data: AlertDraft, today_str: str) -> bool:
    """Insert an alert block directly under its severity section heading.

    Returns False (instead of raising) when the file or the severity section
    is missing — callers surface that as a user-facing warning because a
    malformed ALERTS.md is a documentation problem, not a crash.
    """
    if not os.path.exists(alerts_path):
        get_local_logger().warning("insert_alert: %s does not exist", alerts_path)
        return False
    with open(alerts_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    header = f"## {alert_data['severity']}"
    for i, line in enumerate(lines):
        if header in line:
            block = (
                f"\n### [{alert_data['id']}] {alert_data['title']}\n"
                f"**Severity**: {alert_data['severity']}\n**Status**:   Open\n**Owner**:    None\n"
                f"**Discovered**: {today_str}\n**Impact**: [TBD]\n**Fix**: [TBD]\n"
            )
            lines.insert(i + 1, block)
            with open(alerts_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
    get_local_logger().warning(
        "insert_alert: severity section '%s' not found in %s", header, alerts_path
    )
    return False
