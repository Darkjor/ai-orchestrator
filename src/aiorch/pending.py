"""Parsing and mutation of .ai/PENDING.md — out-of-band manual actions.

WHY this file exists at all: some tasks (running SQL in a cloud console,
rotating credentials, clicking through a dashboard) can NEVER be executed by
an AI agent working in the repo. PENDING.md is the contract between agents
("I discovered this needs doing") and humans ("I did it — resolve the ID").

Format contract (mirrors alerts.py — section position carries the type):
- Action type comes from the ``## Database`` / ``## Infrastructure`` /
  ``## Other`` section the action sits under.
- Actions under ``## DONE`` are invisible to parse_pending but still count
  for next_action_id, so IDs are never reused.
- Action headers look like ``### [DB-001] Title`` (prefix encodes the type).
"""
from __future__ import annotations

import os
import re
import shutil

from aiorch.logs import get_local_logger
from aiorch.models import ActionDraft, PendingAction

_RE_PENDING_HEADER = re.compile(r"### \[([A-Z]+-\d+)\]\s*(.*)")
_RE_HEADING = re.compile(r"^#{1,4}\s")


def ensure_pending_file(pending_path: str) -> None:
    """Copy templates/PENDING.md into place when the file is missing.

    WHY: PENDING.md was introduced in v0.2 — repos initialized with older
    versions of `ai-orch init` won't have it, and every command that writes
    actions must be able to self-heal that gap.
    """
    if os.path.exists(pending_path):
        return
    template = os.path.join(os.path.dirname(__file__), "templates", "PENDING.md")
    shutil.copy(template, pending_path)


def parse_pending(pending_path: str) -> list[PendingAction]:
    """Return open pending actions from PENDING.md (DONE section excluded)."""
    if not os.path.exists(pending_path):
        return []
    actions: list[PendingAction] = []
    current_type = "Other"
    with open(pending_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        s = line.strip()
        if s.startswith("## Database"):
            current_type = "Database"
        elif s.startswith("## Infrastructure"):
            current_type = "Infrastructure"
        elif s.startswith("## Other"):
            current_type = "Other"
        elif s.startswith("## DONE"):
            current_type = "DONE"
        m = _RE_PENDING_HEADER.search(s)
        if m and current_type != "DONE":
            actions.append({"id": m.group(1), "title": m.group(2), "type": current_type})
    return actions


def next_action_id(pending_path: str, prefix: str) -> str:
    """Return the next sequential ID for a prefix (DB, INFRA, ACTION).

    Scans the whole file (including DONE) so resolved actions keep their IDs
    reserved forever — same non-reuse rule as alerts.
    """
    if not os.path.exists(pending_path):
        return f"{prefix}-001"
    with open(pending_path, "r", encoding="utf-8") as f:
        content = f.read()
    numbers = [int(m.group(1)) for m in re.finditer(rf"\[{prefix}-(\d+)\]", content)]
    return f"{prefix}-{(max(numbers) + 1):03d}" if numbers else f"{prefix}-001"


def insert_action(pending_path: str, data: ActionDraft, today_str: str) -> bool:
    """Insert an action block under its type section. Returns True on success.

    The block always embeds a ``ai-orch action-resolve <ID>`` step so the
    human who completes the action knows exactly how to close the loop.
    """
    if not os.path.exists(pending_path):
        get_local_logger().warning("insert_action: %s does not exist", pending_path)
        return False
    type_to_header = {"db": "## Database", "infra": "## Infrastructure", "other": "## Other"}
    header = type_to_header.get(data["type"].lower(), "## Other")
    sql_block = f"\n**SQL**:\n```sql\n{data['sql']}\n```" if data.get("sql") else ""
    steps_line = (
        f"\n**Steps**: {data['steps']}\n1. Run: `ai-orch action-resolve {data['id']}`\n"
        if data.get("steps")
        else f"\n**Steps**: [TBD]\n1. Run: `ai-orch action-resolve {data['id']}`\n"
    )
    block = (
        f"\n### [{data['id']}] {data['title']}\n"
        f"**Status**: Pending\n**Target**: {data.get('target', '[TBD]')}\n**Discovered**: {today_str}"
        f"{sql_block}{steps_line}"
    )
    with open(pending_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if header in line:
            lines.insert(i + 1, block)
            with open(pending_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
    get_local_logger().warning(
        "insert_action: section '%s' not found in %s", header, pending_path
    )
    return False


def resolve_action(pending_path: str, action_id: str) -> bool:
    """Mark an action as Done and move its whole block to the ## DONE section.

    The block is moved (not deleted) so the audit trail of what was done and
    when survives — agents use DONE entries to avoid re-suggesting work.
    """
    if not os.path.exists(pending_path):
        get_local_logger().warning("resolve_action: %s does not exist", pending_path)
        return False
    with open(pending_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = next((i for i, l in enumerate(lines) if re.search(rf"### \[{re.escape(action_id)}\]", l)), -1)
    if start == -1:
        return False
    end = next((j for j in range(start + 1, len(lines)) if _RE_HEADING.match(lines[j])), len(lines))
    block = [l.replace("**Status**: Pending", "**Status**: Done") for l in lines[start:end]]
    remaining = lines[:start] + lines[end:]
    done = next((i for i, l in enumerate(remaining) if l.strip() == "## DONE"), -1)
    if done == -1:
        remaining += ["\n## DONE\n"] + block
    else:
        remaining = remaining[:done + 1] + ["\n"] + block + remaining[done + 1:]
    with open(pending_path, "w", encoding="utf-8") as f:
        f.writelines(remaining)
    return True
