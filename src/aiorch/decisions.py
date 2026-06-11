"""Append-only handling of .ai/DECISIONS.md — the architecture decision log.

WHY append-only: decisions are historical records. Editing past entries would
falsify the project's memory; superseding a decision means appending a new one
that references the old ID. Only `ai-orch handoff` writes here.
"""
from __future__ import annotations

import os
import re

from aiorch.logs import get_local_logger
from aiorch.models import DecisionDraft


def append_decision(decisions_path: str, dec_data: DecisionDraft, today_str: str) -> None:
    """Append a new decision block to DECISIONS.md.

    [TBD] placeholders are intentional: the handoff wizard only captures the
    context in the moment; the deciding agent/human fills Decision/Rationale/
    Consequences in a follow-up edit when the outcome is known.
    """
    if not os.path.exists(decisions_path):
        get_local_logger().warning("append_decision: %s does not exist", decisions_path)
        return
    block = (
        f"\n## [{dec_data['id']}] {dec_data['title']}\n"
        f"**Date**: {today_str}\n"
        f"**Status**: Active\n"
        f"**Context**: {dec_data['context']}\n"
        f"**Decision**: [TBD]\n"
        f"**Rationale**: [TBD]\n"
        f"**Consequences**: [TBD]\n"
        f"**Revisit when**: [TBD]\n"
    )
    with open(decisions_path, "a", encoding="utf-8") as f:
        f.write(block)


def count_decisions(decisions_path: str) -> int:
    """Count decision entries (lines starting with '## [') in DECISIONS.md."""
    if not os.path.exists(decisions_path):
        return 0
    with open(decisions_path, "r", encoding="utf-8") as f:
        content = f.read()
    return len(re.findall(r"^## \[", content, re.MULTILINE))
