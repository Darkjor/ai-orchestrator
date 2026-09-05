"""Typed data contracts shared across all aiorch modules.

WHY this module exists: AI agents (and humans) editing this codebase need to
know the exact shape of the dicts that flow between parsers, renderers and CLI
commands *without* reading every implementation. TypedDicts give that contract
at zero runtime cost — they are plain dicts at runtime, so the Markdown-parsing
code stays simple and the existing test suite keeps passing unchanged.

Rule for contributors: if a function passes a dict between modules, its shape
MUST be declared here first.
"""
from __future__ import annotations

import re
from typing import Optional, TypedDict


class Alert(TypedDict):
    """One open alert parsed from .ai/ALERTS.md.

    Severity is inherited from the ``## P0 / ## P1 / ## P2`` section the alert
    sits under — it is positional, not declared per-alert. Alerts under
    ``## RESOLVED`` are never parsed into this type.
    """

    id: str        # e.g. "ALERT-001"
    title: str
    severity: str  # "P0" | "P1" | "P2"
    status: str    # always "Open" — resolved alerts are filtered at parse time


class AlertDraft(TypedDict):
    """Input payload for inserting a new alert into ALERTS.md."""

    id: str
    title: str
    severity: str


class PendingAction(TypedDict):
    """One open manual action parsed from .ai/PENDING.md.

    ``type`` is the human-readable section name ("Database" | "Infrastructure"
    | "Other"), inherited positionally like Alert.severity. Actions under
    ``## DONE`` are never parsed into this type.
    """

    id: str    # e.g. "DB-001" | "INFRA-001" | "ACTION-001"
    title: str
    type: str


class ActionDraft(TypedDict, total=False):
    """Input payload for inserting a new pending action into PENDING.md.

    ``sql`` and ``steps`` are optional (total=False): db actions usually carry
    SQL, infra/other actions usually carry free-form steps.
    """

    id: str
    title: str
    type: str      # cli value: "db" | "infra" | "other"
    target: str
    sql: Optional[str]
    steps: Optional[str]


class DecisionDraft(TypedDict):
    """Input payload for appending a decision block to DECISIONS.md."""

    id: str        # e.g. "DEC-002"
    title: str
    context: str


class LintRule(TypedDict):
    """One LINT-XXX rule parsed from the '## 4. Lint Rules' section of WHEELS.md.

    ``compiled`` is precomputed at parse time so check_staged_lint never pays
    re.compile() per file/line — rules run inside the pre-commit hook where
    latency is felt by the user on every commit.
    """

    pattern: str
    compiled: re.Pattern[str]
    files: list[str]   # glob patterns matched against the file *basename*
    message: str


class LintViolation(TypedDict):
    """One lint hit reported by check_staged_lint (blocks the commit)."""

    file: str
    line: int
    message: str
    code: str


class ProjectMetrics(TypedDict):
    """Verifiable project health snapshot produced by collect_project_metrics.

    Every value MUST come from a real, re-checkable source (pytest, git, .ai/
    files) — the qa command cross-checks these numbers against live state, so
    inventing or estimating values here breaks the anti-hallucination loop.
    """

    alerts: list[Alert]
    p0: int
    p1: int
    p2: int
    pending: list[PendingAction]
    pending_count: int
    decisions_count: int
    tests_collected: int
    git_modified: int


class EnvelopeError(TypedDict):
    """One contract violation found in a structured inter-agent envelope.

    ``field`` is a dotted/indexed path into the envelope ("steps[0].done_when")
    so an agent can fix the exact field without re-reading the whole schema;
    it is "" for whole-document problems such as invalid JSON.
    """

    field: str
    message: str


class PipelineStep(TypedDict, total=False):
    """One decomposed sub-task produced by the planner role.

    ``done_when`` is what separates a step from an intention: it is the
    condition the executor checks to know it is finished and QA checks to
    judge whether it was. ``depends_on`` holds ids of earlier steps.
    """

    id: str
    goal: str
    done_when: str
    depends_on: list[str]

