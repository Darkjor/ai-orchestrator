"""Backward-compatibility shim — re-exports the domain modules' public API.

WHY this file survives: before v0.3 ALL business logic lived here, and
external code (tests, user scripts, older agents' notes) imports from
``aiorch._helpers``. The logic now lives in single-responsibility modules:

    aiorch.alerts     — ALERTS.md parse/insert/IDs
    aiorch.pending    — PENDING.md parse/insert/resolve/IDs
    aiorch.context    — CONTEXT.md sections, snapshot, export bundle
    aiorch.portability— AGENTS.md / .agents rules, human-readable brief
    aiorch.decisions  — DECISIONS.md append/count
    aiorch.analysis   — analyze/qa metrics pipeline
    aiorch.gitops     — git subprocess wrappers + hook scripts
    aiorch.lint       — WHEELS.md lint rules
    aiorch.config     — config.json loading
    aiorch.models     — TypedDict contracts
    aiorch.logs       — local logging

New code MUST import from those modules directly. This shim only guarantees
that every pre-v0.3 import path (including the underscore-private names)
keeps working. Do not add new logic here.
"""
from __future__ import annotations

from aiorch.alerts import (
    all_alert_ids,
    insert_alert,
    next_alert_id,
    parse_alerts,
)
from aiorch.analysis import (
    collect_project_metrics,
    parse_analysis_status,
    qa_cross_check,
    set_analysis_status,
    write_analysis_report,
)
from aiorch.config import load_config
from aiorch.context import (
    bundle_context,
    generate_snapshot,
    inject_snapshot,
    update_context,
    update_section,
    read_section,
)
from aiorch.decisions import append_decision, count_decisions
from aiorch.gitops import (
    GitCommandError,
    find_secret_files,
    get_staged_files,
    has_merge_conflicts,
    run_git_commit,
    scan_conflict_files,
    get_recent_changed_files,
)
from aiorch.portability import (
    AGENTS_MD_BLOCK,
    ANTIGRAVITY_RULE,
    render_brief,
    write_managed_block,
)
from aiorch.lint import check_staged_lint, parse_lint_rules
from aiorch.pending import (
    ensure_pending_file,
    insert_action,
    next_action_id,
    parse_pending,
    resolve_action,
)

# Legacy private-name aliases (pre-v0.3 API). Same objects, old names.
_all_alert_ids = all_alert_ids
_next_alert_id = next_alert_id
_insert_alert = insert_alert
_next_action_id = next_action_id
_insert_action = insert_action
_resolve_action = resolve_action
_has_merge_conflicts = has_merge_conflicts

__all__ = [
    "AGENTS_MD_BLOCK",
    "ANTIGRAVITY_RULE",
    "GitCommandError",
    "_all_alert_ids",
    "_has_merge_conflicts",
    "_insert_action",
    "_insert_alert",
    "_next_action_id",
    "_next_alert_id",
    "_resolve_action",
    "all_alert_ids",
    "append_decision",
    "bundle_context",
    "check_staged_lint",
    "collect_project_metrics",
    "count_decisions",
    "ensure_pending_file",
    "find_secret_files",
    "generate_snapshot",
    "get_recent_changed_files",
    "get_staged_files",
    "has_merge_conflicts",
    "inject_snapshot",
    "insert_action",
    "insert_alert",
    "load_config",
    "next_action_id",
    "next_alert_id",
    "parse_alerts",
    "parse_analysis_status",
    "parse_lint_rules",
    "parse_pending",
    "qa_cross_check",
    "read_section",
    "render_brief",
    "resolve_action",
    "run_git_commit",
    "scan_conflict_files",
    "set_analysis_status",
    "update_context",
    "update_section",
    "write_analysis_report",
    "write_managed_block",
]
