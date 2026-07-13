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

