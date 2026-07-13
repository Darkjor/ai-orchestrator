import os
from unittest.mock import MagicMock, patch

import pytest

from aiorch.observability import SupabaseLogger, get_logger


def test_logger_disabled_when_no_env_vars(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    logger = SupabaseLogger()
    assert logger.enabled is False


def test_logger_disabled_when_only_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    logger = SupabaseLogger()
    assert logger.enabled is False


def test_log_run_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    logger = SupabaseLogger()
    # Should not raise even with no Supabase configured
    logger.log_run("test-agent", "analyze", latency_ms=100)


def test_get_recent_runs_returns_empty_when_disabled(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    logger = SupabaseLogger()
    assert logger.get_recent_runs() == []


def test_logger_enabled_with_mock_client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "fake-key")
    mock_client = MagicMock()
    with patch("aiorch.observability.SupabaseLogger.__init__") as mock_init:
        mock_init.return_value = None
        logger = SupabaseLogger.__new__(SupabaseLogger)
        logger._enabled = True
        logger._client = mock_client
        assert logger.enabled is True


def test_log_run_calls_insert_when_enabled():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
    logger = SupabaseLogger.__new__(SupabaseLogger)
    logger._enabled = True
    logger._client = mock_client
    logger.log_run("analyze", "analyze", latency_ms=250, status="ok")
    mock_client.table.assert_called_once_with("agent_runs")
    mock_client.table.return_value.insert.assert_called_once()
    call_args = mock_client.table.return_value.insert.call_args[0][0]
    assert call_args["agent_id"] == "analyze"
    assert call_args["latency_ms"] == 250
    assert call_args["status"] == "ok"


def test_log_run_swallows_exception_when_enabled():
    mock_client = MagicMock()
    mock_client.table.side_effect = RuntimeError("network error")
    logger = SupabaseLogger.__new__(SupabaseLogger)
    logger._enabled = True
    logger._client = mock_client
    # Must not raise
    logger.log_run("analyze", "analyze")


def test_get_recent_runs_returns_data_when_enabled():
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.data = [
        {"agent_id": "analyze", "command": "analyze", "latency_ms": 100, "status": "ok"}
    ]
    mock_client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_result
    logger = SupabaseLogger.__new__(SupabaseLogger)
    logger._enabled = True
    logger._client = mock_client
    runs = logger.get_recent_runs(limit=5)
    assert len(runs) == 1
    assert runs[0]["agent_id"] == "analyze"


def test_get_recent_runs_swallows_exception():
    mock_client = MagicMock()
    mock_client.table.side_effect = RuntimeError("connection failed")
    logger = SupabaseLogger.__new__(SupabaseLogger)
    logger._enabled = True
    logger._client = mock_client
    result = logger.get_recent_runs()
    assert result == []


def test_get_logger_returns_singleton(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    import aiorch.observability as obs_mod
    obs_mod._logger = None  # reset singleton for test isolation
    logger1 = get_logger()
    logger2 = get_logger()
    assert logger1 is logger2


def test_logger_package_missing_sets_reason(monkeypatch):
    import sys
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "fake-key")
    monkeypatch.setitem(sys.modules, "supabase", None)
    logger = SupabaseLogger()
    assert logger.enabled is False
    assert logger.disabled_reason == "package_missing"


def test_logger_env_missing_sets_reason(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    logger = SupabaseLogger()
    assert logger.enabled is False
    assert logger.disabled_reason == "env_missing"


def test_log_run_failure_is_logged(caplog):
    import logging
    mock_client = MagicMock()
    mock_client.table.side_effect = RuntimeError("network error")
    logger = SupabaseLogger.__new__(SupabaseLogger)
    logger._enabled = True
    logger._client = mock_client
    with caplog.at_level(logging.WARNING, logger="aiorch"):
        logger.log_run("analyze", "analyze")
    assert "log_run failed" in caplog.text


def test_get_recent_runs_failure_is_logged(caplog):
    import logging
    mock_client = MagicMock()
    mock_client.table.side_effect = RuntimeError("connection failed")
    logger = SupabaseLogger.__new__(SupabaseLogger)
    logger._enabled = True
    logger._client = mock_client
    with caplog.at_level(logging.WARNING, logger="aiorch"):
        result = logger.get_recent_runs()
    assert result == []
    assert "get_recent_runs failed" in caplog.text
