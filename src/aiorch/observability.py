import os
import time
from typing import Optional


class SupabaseLogger:
    """Observability logger that writes agent run metrics to Supabase.

    Disabled automatically when SUPABASE_URL / SUPABASE_ANON_KEY are absent.
    Never raises — all Supabase errors are swallowed so the CLI keeps working.
    """

    def __init__(self) -> None:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
        self._enabled = bool(url and key)
        self._client = None
        if self._enabled:
            try:
                from supabase import create_client  # lazy — only needed when configured
                self._client = create_client(url, key)
            except Exception:
                self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def log_run(
        self,
        agent_id: str,
        command: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int = 0,
        cost_usd: float = 0.0,
        status: str = "ok",
        eval_score: Optional[float] = None,
    ) -> None:
        if not self._enabled or self._client is None:
            return
        try:
            self._client.table("agent_runs").insert(
                {
                    "agent_id": agent_id,
                    "command": command,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "latency_ms": latency_ms,
                    "cost_usd": cost_usd,
                    "status": status,
                    "eval_score": eval_score,
                }
            ).execute()
        except Exception:
            pass  # never let observability break the CLI

    def get_recent_runs(self, limit: int = 20) -> list:
        if not self._enabled or self._client is None:
            return []
        try:
            result = (
                self._client.table("agent_runs")
                .select("agent_id,command,timestamp,latency_ms,cost_usd,status,eval_score")
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception:
            return []


_logger: Optional[SupabaseLogger] = None


def get_logger() -> SupabaseLogger:
    """Return the shared SupabaseLogger instance (singleton, lazy-init)."""
    global _logger
    if _logger is None:
        _logger = SupabaseLogger()
    return _logger
