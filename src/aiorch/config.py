"""Loading of .ai/config.json — project metadata and model-routing rules.

WHY a forgiving loader: config.json is hand-edited by humans and rewritten by
AI agents; a single trailing comma must degrade the CLI to sensible defaults,
never crash it. Callers detect the "file exists but is corrupt" case with
``os.path.exists(path) and not load_config(path)`` and warn the user.
"""
from __future__ import annotations

import json
import os
from typing import Any

from aiorch.logs import get_local_logger


def load_config(config_path: str) -> dict[str, Any]:
    """Load config.json as a dict. Returns {} on missing or corrupt file."""
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        get_local_logger().warning("config.json unreadable (%s): %s", config_path, exc)
        return {}
