"""Contract tests for the v0.3 domain modules.

These cover what tests/test_cli.py cannot see from the CLI surface:
gitops error paths, the local logger, the PENDING.md self-heal, and the
backward-compatibility guarantee of the aiorch._helpers shim.
"""
import logging
import os

import pytest

import aiorch.logs as aiorch_logs
from aiorch.gitops import (GitCommandError, PRE_COMMIT_HOOK, find_secret_files,
                           get_staged_files, run_git_commit,
                           scan_conflict_files, write_git_hook)
from aiorch.pending import ensure_pending_file


# ---------------------------------------------------------------------------
# _helpers backward-compat shim — frozen public API (see docs/AI_ARCHITECTURE.md)
# ---------------------------------------------------------------------------

def test_helpers_shim_reexports_legacy_names():
    """Pre-v0.3 import paths (including underscore-private names) must keep working."""
    from aiorch import _helpers
    from aiorch.alerts import insert_alert, next_alert_id
    from aiorch.pending import next_action_id, resolve_action

    assert _helpers._next_alert_id is next_alert_id
    assert _helpers._insert_alert is insert_alert
    assert _helpers._next_action_id is next_action_id
    assert _helpers._resolve_action is resolve_action
    # Public names still importable from the shim too
    assert callable(_helpers.parse_alerts)
    assert callable(_helpers.parse_lint_rules)
    assert callable(_helpers.update_section)
    assert callable(_helpers._has_merge_conflicts)


# ---------------------------------------------------------------------------
# gitops error contract
# ---------------------------------------------------------------------------

def test_get_staged_files_raises_outside_git_repo(tmp_path):
    """Query functions must raise GitCommandError (not return []) on git failure."""
    os.chdir(tmp_path)
    with pytest.raises(GitCommandError):
        get_staged_files()


def test_run_git_commit_reports_failure_outside_repo(tmp_path):
    """Mutation functions report failure as (False, detail), never raise."""
    os.chdir(tmp_path)
    ok, detail = run_git_commit("1", "feat", "should fail")
    assert ok is False
    assert "git add failed" in detail


def test_run_git_commit_returns_error_when_git_missing(monkeypatch):
    """run_git_commit must return (False, error) if subprocess.run raises OSError."""
    import subprocess
    def raiser(*args, **kwargs):
        raise FileNotFoundError("[WinError 2] El sistema no puede encontrar el archivo especificado")
    monkeypatch.setattr(subprocess, "run", raiser)
    ok, detail = run_git_commit("1", "feat", "missing git")
    assert ok is False
    assert "git add failed" in detail


def test_find_secret_files_detects_common_suffixes(tmp_path):
    os.chdir(tmp_path)
    for name in (".env", "server.pem", "deploy.key", "safe.txt"):
        with open(name, "w") as f:
            f.write("x")
    found = find_secret_files()
    assert ".env" in found
    assert "server.pem" in found
    assert "deploy.key" in found
    assert "safe.txt" not in found


def test_scan_conflict_files_requires_marker_pair(tmp_path):
    """Only files with BOTH <<<<<<< and ======= lines count — avoids Markdown
    horizontal-rule false positives."""
    os.chdir(tmp_path)
    (tmp_path / "real.py").write_text(
        "<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8"
    )
    (tmp_path / "partial.md").write_text("<<<<<<< just an arrow line\n", encoding="utf-8")
    found = scan_conflict_files(".")
    assert any("real.py" in f for f in found)
    assert not any("partial.md" in f for f in found)


def test_scan_conflict_files_skips_vendored_dirs(tmp_path):
    os.chdir(tmp_path)
    vendored = tmp_path / "node_modules"
    vendored.mkdir()
    (vendored / "dep.js").write_text(
        "<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> b\n", encoding="utf-8"
    )
    assert scan_conflict_files(".") == []


def test_write_git_hook_writes_lf_content(tmp_path):
    path, warning = write_git_hook(str(tmp_path), "pre-commit", PRE_COMMIT_HOOK)
    assert os.path.exists(path)
    with open(path, "rb") as f:
        raw = f.read()
    assert b"\r\n" not in raw  # sh on Windows rejects CRLF shebangs
    assert b"ai-orch check" in raw


# ---------------------------------------------------------------------------
# pending self-heal
# ---------------------------------------------------------------------------

def test_ensure_pending_file_copies_template(tmp_path):
    pending = tmp_path / "PENDING.md"
    ensure_pending_file(str(pending))
    content = pending.read_text(encoding="utf-8")
    assert "## Database" in content
    assert "## DONE" in content
    # Idempotent: a second call must not clobber existing content
    pending.write_text(content + "\n### [DB-001] keep me\n", encoding="utf-8")
    ensure_pending_file(str(pending))
    assert "keep me" in pending.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# local logger
# ---------------------------------------------------------------------------

def _reset_aiorch_logger():
    logger = logging.getLogger("aiorch")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    aiorch_logs._configured = False


def test_local_logger_is_singleton_without_duplicate_handlers():
    _reset_aiorch_logger()
    try:
        first = aiorch_logs.get_local_logger()
        handler_count = len(first.handlers)
        second = aiorch_logs.get_local_logger()
        assert first is second
        assert len(second.handlers) == handler_count  # no duplicates on re-call
    finally:
        _reset_aiorch_logger()


def test_local_logger_writes_file_when_ai_folder_exists(tmp_path):
    os.chdir(tmp_path)
    os.makedirs(".ai")
    _reset_aiorch_logger()
    try:
        log = aiorch_logs.get_local_logger()
        log.warning("disk trail for agents")
        log_file = tmp_path / ".ai" / "logs" / "aiorch.log"
        assert log_file.exists()
        assert "disk trail for agents" in log_file.read_text(encoding="utf-8")
    finally:
        _reset_aiorch_logger()


def test_update_context_logs_when_markers_missing(tmp_path, caplog):
    """update_context must warn when accomplishments or changed_files markers are missing."""
    import logging
    from aiorch.context import update_context
    context_file = tmp_path / "CONTEXT.md"
    context_file.write_text("## Current State (updated: 2026-01-01)\nSome text without markers.\n", encoding="utf-8")
    
    with caplog.at_level(logging.WARNING, logger="aiorch"):
        res = update_context(str(context_file), "2026-07-12", "did X", "file.py")
    
    assert res is True
    content = context_file.read_text(encoding="utf-8")
    assert "2026-01-01" not in content  # date should be updated
    assert "did X" not in content
    assert "file.py" not in content
    assert any("What works right now" in record.message for record in caplog.records)
    assert any("Most recently changed" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# analysis.py tests
# ---------------------------------------------------------------------------

def test_parse_analysis_status_missing_file():
    from aiorch.analysis import parse_analysis_status
    assert parse_analysis_status("nonexistent.md") == "NOT_FOUND"


def test_set_analysis_status_roundtrip(tmp_path):
    from aiorch.analysis import parse_analysis_status, set_analysis_status
    analysis_path = tmp_path / "ANALYSIS.md"
    analysis_path.write_text("# Analysis\n\n## Status\nPENDING\n", encoding="utf-8")
    
    assert parse_analysis_status(str(analysis_path)) == "PENDING"
    set_analysis_status(str(analysis_path), "QA_APPROVED")
    assert parse_analysis_status(str(analysis_path)) == "QA_APPROVED"
    assert set_analysis_status(str(tmp_path / "nonexistent.md"), "QA_APPROVED") is False


def test_write_analysis_report_then_qa_cross_check_clean(tmp_path):
    from aiorch.analysis import write_analysis_report, qa_cross_check
    
    analysis_path = tmp_path / "ANALYSIS.md"
    metrics = {
        "alerts": [],
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "pending": [],
        "pending_count": 0,
        "decisions_count": 0,
        "tests_collected": 0,
        "git_modified": 0,
    }
    write_analysis_report(str(analysis_path), metrics, "qa_reviewer", "2026-07-12")
    
    (tmp_path / "ALERTS.md").write_text("## P0\n\n## P1\n\n## P2\n", encoding="utf-8")
    (tmp_path / "PENDING.md").write_text("## Database\n\n## Infrastructure\n\n## Other\n\n## DONE\n", encoding="utf-8")
    
    issues = qa_cross_check(str(analysis_path), str(tmp_path))
    assert issues == []


def test_qa_cross_check_detects_p0_drift(tmp_path):
    from aiorch.analysis import write_analysis_report, qa_cross_check
    
    analysis_path = tmp_path / "ANALYSIS.md"
    metrics = {
        "alerts": [],
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "pending": [],
        "pending_count": 0,
        "decisions_count": 0,
        "tests_collected": 0,
        "git_modified": 0,
    }
    write_analysis_report(str(analysis_path), metrics, "qa_reviewer", "2026-07-12")
    
    (tmp_path / "ALERTS.md").write_text("## P0\n### [ALERT-001] Blocker\n\n## P1\n\n## P2\n", encoding="utf-8")
    (tmp_path / "PENDING.md").write_text("## Database\n\n## Infrastructure\n\n## Other\n\n## DONE\n", encoding="utf-8")
    
    issues = qa_cross_check(str(analysis_path), str(tmp_path))
    assert len(issues) == 1
    assert "P0" in issues[0]


def test_collect_project_metrics_offline(tmp_path):
    from aiorch.analysis import collect_project_metrics
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()
    (ai_dir / "ALERTS.md").write_text("## P0\n\n## P1\n\n## P2\n", encoding="utf-8")
    (ai_dir / "PENDING.md").write_text("## Database\n\n## Infrastructure\n\n## Other\n\n## DONE\n", encoding="utf-8")
    (ai_dir / "DECISIONS.md").write_text("## Decisions\n", encoding="utf-8")
    
    metrics = collect_project_metrics(str(ai_dir))
    assert metrics["p0"] == 0
    assert metrics["pending_count"] == 0
    assert metrics["decisions_count"] == 0
    assert "tests_collected" in metrics
    assert "git_modified" in metrics


# ---------------------------------------------------------------------------
# context.py tests
# ---------------------------------------------------------------------------

def test_update_section_prefix_case_insensitive(tmp_path):
    from aiorch.context import update_section
    f = tmp_path / "FILE.md"
    f.write_text("## SECTION A\nOld value\n---", encoding="utf-8")
    
    res = update_section(str(f), "section a", "New value")
    assert res is True
    content = f.read_text(encoding="utf-8")
    assert "New value" in content
    assert "Old value" not in content


def test_update_section_missing_returns_false(tmp_path):
    from aiorch.context import update_section
    f = tmp_path / "FILE.md"
    f.write_text("## SECTION A\nValue\n", encoding="utf-8")
    res = update_section(str(f), "section b", "New value")
    assert res is False


def test_update_context_prepends_accomplishments_and_replaces_changed(tmp_path):
    from aiorch.context import update_context
    f = tmp_path / "CONTEXT.md"
    f.write_text("## Current State (updated: 2026-01-01)\n**What works right now:**\n- old acc\n\n**Most recently changed:**\n- old changed\n", encoding="utf-8")
    
    res = update_context(str(f), "2026-07-12", "new acc 1", "new changed 1")
    assert res is True
    content = f.read_text(encoding="utf-8")
    assert "- new acc 1" in content
    assert "- old acc" in content
    assert "- new changed 1" in content
    assert "- old changed" not in content
    
    res = update_context(str(f), "2026-07-13", "new acc 2", "new changed 2")
    assert res is True
    content = f.read_text(encoding="utf-8")
    assert "- new acc 2" in content
    assert "- new acc 1" in content
    assert "- old acc" in content
    assert "- new changed 2" in content
    assert "- new changed 1" not in content


def test_inject_snapshot_upsert_no_duplicates(tmp_path):
    from aiorch.context import inject_snapshot
    f = tmp_path / "CONTEXT.md"
    f.write_text("## Codebase Snapshot\nOld snap\n", encoding="utf-8")
    
    inject_snapshot(str(f), "New snap 1")
    content = f.read_text(encoding="utf-8")
    assert content.count("## Codebase Snapshot") == 1
    assert "New snap 1" in content
    
    inject_snapshot(str(f), "New snap 2")
    content = f.read_text(encoding="utf-8")
    assert content.count("## Codebase Snapshot") == 1
    assert "New snap 2" in content
    assert "New snap 1" not in content


def test_bundle_context_reading_order(tmp_path):
    from aiorch.context import bundle_context
    (tmp_path / "ORCHESTRATOR.md").write_text("Manual content\n", encoding="utf-8")
    (tmp_path / "CONTEXT.md").write_text("Context content\n", encoding="utf-8")
    (tmp_path / "ALERTS.md").write_text("Alerts content\n", encoding="utf-8")
    (tmp_path / "DECISIONS.md").write_text("Decisions content\n", encoding="utf-8")
    
    bundle = bundle_context(str(tmp_path))
    assert "Manual content" in bundle
    assert "Context content" in bundle
    assert "Alerts content" in bundle
    idx_manual = bundle.index("Manual content")
    idx_context = bundle.index("Context content")
    idx_alerts = bundle.index("Alerts content")
    assert idx_manual < idx_context < idx_alerts


# ---------------------------------------------------------------------------
# decisions.py tests
# ---------------------------------------------------------------------------

def test_count_decisions(tmp_path):
    from aiorch.decisions import count_decisions, append_decision
    dec_path = tmp_path / "DECISIONS.md"
    assert count_decisions(str(dec_path)) == 0
    
    dec_path.write_text("## Design Decisions\n", encoding="utf-8")
    assert count_decisions(str(dec_path)) == 0
    
    append_decision(str(dec_path), {"id": "DEC-001", "title": "Test dec 1", "context": "Rationale 1"}, "2026-07-12")
    assert count_decisions(str(dec_path)) == 1
    
    append_decision(str(dec_path), {"id": "DEC-002", "title": "Test dec 2", "context": "Rationale 2"}, "2026-07-13")
    assert count_decisions(str(dec_path)) == 2


def test_append_decision_missing_file_logs(tmp_path, caplog):
    import logging
    from aiorch.decisions import append_decision
    dec_path = tmp_path / "nonexistent" / "DECISIONS.md"
    
    with caplog.at_level(logging.WARNING, logger="aiorch"):
        append_decision(str(dec_path), {"id": "DEC-001", "title": "Test dec 1", "context": "Rationale 1"}, "2026-07-12")
    assert any("does not exist" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# config.py tests
# ---------------------------------------------------------------------------

def test_load_config_corrupt_returns_empty_and_logs(tmp_path, caplog):
    import logging
    from aiorch.config import load_config
    conf_path = tmp_path / "config.json"
    conf_path.write_text("{ corrupt json }", encoding="utf-8")
    
    with caplog.at_level(logging.WARNING, logger="aiorch"):
        config = load_config(str(conf_path))
    assert config == {}
    assert any("unreadable" in record.message for record in caplog.records)



# ---------------------------------------------------------------------------
# portability.py tests
# ---------------------------------------------------------------------------

def test_write_managed_block_reports_created_updated_unchanged(tmp_path):
    from aiorch.portability import write_managed_block, MANAGED_START
    target = tmp_path / "AGENTS.md"
    assert write_managed_block(str(target), "hello", title="T") == "created"
    assert write_managed_block(str(target), "hello", title="T") == "unchanged"
    assert write_managed_block(str(target), "goodbye", title="T") == "updated"
    text = target.read_text(encoding="utf-8")
    assert "goodbye" in text and "hello" not in text
    assert text.count(MANAGED_START) == 1


def test_write_managed_block_appends_to_unmarked_file(tmp_path):
    from aiorch.portability import write_managed_block
    target = tmp_path / "AGENTS.md"
    target.write_text("# Mine\n\nHand-written rules.\n", encoding="utf-8")
    assert write_managed_block(str(target), "generated") == "updated"
    text = target.read_text(encoding="utf-8")
    assert "Hand-written rules." in text and "generated" in text


def test_write_managed_block_creates_parent_directory(tmp_path):
    from aiorch.portability import write_managed_block
    target = tmp_path / "deep" / "nested" / "rules.md"
    assert write_managed_block(str(target), "x") == "created"
    assert target.exists()


def test_render_brief_on_empty_project(tmp_path):
    from aiorch.portability import render_brief
    (tmp_path / ".ai").mkdir()
    brief = render_brief(str(tmp_path / ".ai"), {"project_name": "demo"}, "2026-08-31")
    assert "demo — project status" in brief
    assert "No open blockers." in brief
    assert "Nothing waiting." in brief


def test_render_brief_orders_alerts_by_severity(tmp_path):
    from aiorch.alerts import insert_alert
    from aiorch.portability import render_brief
    import shutil, os as _os
    ai = tmp_path / ".ai"
    ai.mkdir()
    tpl = _os.path.join(_os.path.dirname(__import__("aiorch").__file__), "templates", "ALERTS.md")
    shutil.copy(tpl, ai / "ALERTS.md")
    p = str(ai / "ALERTS.md")
    insert_alert(p, {"id": "ALERT-001", "title": "low", "severity": "P2"}, "2026-08-31")
    insert_alert(p, {"id": "ALERT-002", "title": "fire", "severity": "P0"}, "2026-08-31")
    brief = render_brief(str(ai), {}, "2026-08-31")
    assert brief.index("ALERT-002") < brief.index("ALERT-001")
    assert "blocking issue" in brief


def test_antigravity_rule_has_valid_frontmatter():
    from aiorch.portability import ANTIGRAVITY_RULE
    assert ANTIGRAVITY_RULE.startswith("---\n")
    fm = ANTIGRAVITY_RULE.split("---", 2)[1]
    assert "trigger: always_on" in fm
    assert "description:" in fm
    # Antigravity caps each rules file at 12,000 characters.
    assert len(ANTIGRAVITY_RULE) < 12000


def test_read_section_roundtrips_with_update_section(tmp_path):
    from aiorch.context import read_section, update_section
    f = tmp_path / "CONTEXT.md"
    f.write_text("## Current State (updated: x)\n\nold\n\n## Next\n\nkeep\n", encoding="utf-8")
    assert update_section(str(f), "Current State", "fresh value")
    assert read_section(str(f), "Current State") == "fresh value"
    assert read_section(str(f), "Next") == "keep"
    assert read_section(str(f), "Nonexistent") == ""


def test_get_recent_changed_files_raises_without_git(tmp_path):
    import os as _os
    from aiorch.gitops import GitCommandError, get_recent_changed_files
    _os.chdir(tmp_path)
    with pytest.raises(GitCommandError):
        get_recent_changed_files()


# ---------------------------------------------------------------------------
# pipeline.py — the structured inter-agent contract
# ---------------------------------------------------------------------------

def _planner(**over):
    env = {
        "schema": "ai-orch/v1", "role": "planner", "task_id": "T-1", "status": "ok",
        "summary": "plan", "next_role": "executor", "evidence": ["read src/"],
        "steps": [{"id": "S-1", "goal": "do a thing", "done_when": "tests pass"}],
    }
    env.update(over)
    return env


def test_valid_planner_envelope_has_no_errors():
    from aiorch.pipeline import validate_envelope
    assert validate_envelope(_planner()) == []


def test_illegal_transition_is_rejected():
    from aiorch.pipeline import validate_envelope
    errs = validate_envelope(_planner(next_role="qa"))
    assert any(e["field"] == "next_role" for e in errs)


def test_nothing_routes_back_to_planner():
    from aiorch.pipeline import TRANSITIONS
    assert all("planner" not in targets for targets in TRANSITIONS.values())


def test_step_without_done_when_is_rejected():
    from aiorch.pipeline import validate_envelope
    errs = validate_envelope(_planner(steps=[{"id": "S-1", "goal": "g"}]))
    assert any(e["field"] == "steps[0].done_when" for e in errs)


def test_duplicate_and_unknown_step_ids_are_rejected():
    from aiorch.pipeline import validate_envelope
    dupes = validate_envelope(_planner(steps=[
        {"id": "S-1", "goal": "a", "done_when": "x"},
        {"id": "S-1", "goal": "b", "done_when": "y"},
    ]))
    assert any("duplicate" in e["message"] for e in dupes)
    unknown = validate_envelope(_planner(steps=[
        {"id": "S-1", "goal": "a", "done_when": "x", "depends_on": ["S-9"]},
    ]))
    assert any("unknown step id" in e["message"] for e in unknown)


def test_ok_status_requires_evidence():
    from aiorch.pipeline import validate_envelope
    errs = validate_envelope(_planner(evidence=[]))
    assert any(e["field"] == "evidence" for e in errs)


def test_blocked_status_requires_blocked_on():
    from aiorch.pipeline import validate_envelope
    errs = validate_envelope(_planner(status="blocked", evidence=[]))
    assert any(e["field"] == "blocked_on" for e in errs)


def test_qa_cannot_approve_over_a_p0():
    from aiorch.pipeline import validate_envelope
    errs = validate_envelope({
        "schema": "ai-orch/v1", "role": "qa", "task_id": "T-1", "status": "ok",
        "summary": "s", "next_role": "none", "evidence": ["pytest"],
        "verdict": "approved",
        "findings": [{"severity": "P0", "claim": "leak", "evidence": "line 42"}],
    })
    assert any(e["field"] == "verdict" for e in errs)


def test_qa_finding_requires_evidence():
    from aiorch.pipeline import validate_envelope
    errs = validate_envelope({
        "schema": "ai-orch/v1", "role": "qa", "task_id": "T-1", "status": "ok",
        "summary": "s", "next_role": "executor", "evidence": ["pytest"],
        "verdict": "rejected", "findings": [{"severity": "P1", "claim": "slow"}],
    })
    assert any(e["field"] == "findings[0].evidence" for e in errs)


def test_executor_change_needs_a_reason():
    from aiorch.pipeline import validate_envelope
    errs = validate_envelope({
        "schema": "ai-orch/v1", "role": "executor", "task_id": "T-1", "status": "ok",
        "summary": "s", "next_role": "qa", "evidence": ["pytest"],
        "changes": [{"path": "src/a.py", "action": "modified"}],
    })
    assert any(e["field"] == "changes[0].why" for e in errs)


def test_non_object_envelope_is_rejected_not_crashed():
    from aiorch.pipeline import validate_envelope
    assert validate_envelope(["not", "an", "object"])
    assert validate_envelope(None)


def test_load_envelope_reports_bad_json_as_a_violation(tmp_path):
    from aiorch.pipeline import load_envelope
    bad = tmp_path / "e.json"
    bad.write_text("{not json", encoding="utf-8")
    data, errors = load_envelope(str(bad))
    assert data is None and errors and "not valid JSON" in errors[0]["message"]


def test_next_step_stops_on_blocked_or_failed():
    from aiorch.pipeline import next_step
    assert next_step({"status": "ok", "next_role": "qa"}) == "qa"
    assert next_step({"status": "blocked", "next_role": "qa"}) == "none"
    assert next_step({"status": "failed", "next_role": "qa"}) == "none"


def test_role_versions_flags_unversioned_prompts():
    from aiorch.pipeline import role_versions
    got = role_versions({"agents": {"planner": {"version": "1.2.0"}, "executor": {}}})
    assert got == [("executor", "unversioned"), ("planner", "1.2.0")]
    assert role_versions({}) == []


# ---------------------------------------------------------------------------
# The commit guard must not accept machine-written changes as a record
# ---------------------------------------------------------------------------

_BASE_CONTEXT = "## Current State\n\nreal content\n"


def _with_snapshot(base):
    """Mimic inject_snapshot: separator rule, then the generated section."""
    return base.rstrip() + "\n\n---\n\n## Codebase Snapshot\n\n- src/a.py: fn\n"


def test_strip_snapshot_also_drops_the_separator_rule():
    from aiorch.context import strip_snapshot
    # The rule inject_snapshot writes must go too, or an otherwise-identical
    # file compares as changed and the guard is fooled.
    assert strip_snapshot(_with_snapshot(_BASE_CONTEXT)) == strip_snapshot(_BASE_CONTEXT)


def test_strip_snapshot_keeps_a_rule_the_user_wrote():
    from aiorch.context import strip_snapshot
    assert "---" in strip_snapshot("## A\ntext\n\n---\n\n## B\nmore\n")


def test_snapshot_only_change_does_not_count_as_recorded():
    from aiorch.context import staged_context_records_something
    assert not staged_context_records_something(_with_snapshot(_BASE_CONTEXT), _BASE_CONTEXT)


def test_real_edit_alongside_a_snapshot_still_counts():
    from aiorch.context import staged_context_records_something
    edited = _with_snapshot("## Current State\n\nstopped at the JWT refresh\n")
    assert staged_context_records_something(edited, _BASE_CONTEXT)


def test_missing_blobs_count_as_recorded():
    from aiorch.context import staged_context_records_something
    # Nothing to compare against (first commit, new file) — the safe reading.
    assert staged_context_records_something(None, _BASE_CONTEXT)
    assert staged_context_records_something(_BASE_CONTEXT, None)


def test_guard_ignores_snapshot_and_logs_but_sees_real_context():
    from aiorch.context import classify_staged_paths
    same = lambda ref: _with_snapshot(_BASE_CONTEXT) if ref.startswith(":") else _BASE_CONTEXT

    # Code + a snapshot-only CONTEXT.md + the tool's own log = nothing recorded.
    code, recorded = classify_staged_paths(
        ["src/a.py", ".ai/CONTEXT.md", ".ai/logs/aiorch.log"], same)
    assert code and not recorded

    # The same staging plus a real ALERTS.md edit does count.
    code, recorded = classify_staged_paths(
        ["src/a.py", ".ai/CONTEXT.md", ".ai/ALERTS.md"], same)
    assert code and recorded


def test_guard_exempts_docs_and_packaging():
    from aiorch.context import classify_staged_paths
    code, recorded = classify_staged_paths(
        ["docs/API.md", ".gitignore", "pyproject.toml"], lambda r: None)
    assert not code and not recorded


def test_init_writes_ai_gitignore_and_never_clobbers_one(tmp_path):
    import os as _os
    from aiorch.logs import write_ai_gitignore
    ai = tmp_path / ".ai"
    ai.mkdir()
    assert write_ai_gitignore(str(ai)) is True
    assert "logs/" in (ai / ".gitignore").read_text(encoding="utf-8")
    (ai / ".gitignore").write_text("mine\n", encoding="utf-8")
    assert write_ai_gitignore(str(ai)) is False
    assert (ai / ".gitignore").read_text(encoding="utf-8") == "mine\n"
