"""The structured envelope agents pass between each other, and its validation.

WHY this module exists: prose between agents is the failure point. When a
planner hands an executor a paragraph, the executor has to *interpret* it, and
interpretation is where hallucination enters. An envelope the CLI can parse
removes the interpretation step — the next agent consumes fields, and a
malformed handoff fails loudly at the boundary instead of quietly downstream.

The contract this enforces, in order of what actually catches bugs:

1. **Shape** — required fields per role. A planner that returns no steps has
   not planned; that is an error, not an empty result.
2. **Legal transitions** — planner -> executor -> qa, and qa either sends work
   back to the executor or ends the chain. A role cannot hand to itself, and
   nothing may hand back to the planner: re-planning starts a new chain with a
   new task_id, so a chain can never loop forever.
3. **Evidence** — a step reporting `ok` must cite something checkable. This is
   the same rule `analysis.py` enforces on metrics, applied to the chain: a
   claim without evidence is the shape hallucination takes.

Deliberately NOT enforced here: whether the work is *good*. Schema validity is
a floor, not a review — that is what the QA role is for, and conflating them
would let a well-formed envelope pass as correct work.

Format note: JSON, not XML tags. Both are parseable, but JSON is what a CLI
validates without a grammar, and it is what `output_config.format` (structured
outputs) emits natively — so the model is constrained at generation time rather
than asked to behave in prose. See skills/pipeline/SKILL.md.
"""
from __future__ import annotations

import json
import os
from typing import Any

from aiorch.logs import get_local_logger
from aiorch.models import EnvelopeError

SCHEMA_ID = "ai-orch/v1"

ROLES = ("planner", "executor", "qa")
STATUSES = ("ok", "blocked", "failed")
SEVERITIES = ("P0", "P1", "P2")

# planner -> executor -> qa -> (executor | end). Nothing routes back to the
# planner: re-planning is a NEW chain with a new task_id, which is what stops
# a pipeline from cycling without a human ever seeing it.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "planner": ("executor",),
    "executor": ("qa",),
    "qa": ("executor", "none"),
}

# Fields every envelope carries, plus the ones that only make sense per role.
_COMMON_REQUIRED = ("schema", "role", "task_id", "status", "summary", "next_role")
_ROLE_REQUIRED: dict[str, tuple[str, ...]] = {
    "planner": ("steps",),
    "executor": ("changes",),
    "qa": ("verdict", "findings"),
}


def _err(field: str, message: str) -> EnvelopeError:
    return {"field": field, "message": message}


def _validate_steps(steps: Any, errors: list[EnvelopeError]) -> None:
    if not isinstance(steps, list) or not steps:
        errors.append(_err("steps", "planner must return a non-empty list of steps"))
        return
    seen: set[str] = set()
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(_err(f"steps[{i}]", "each step must be an object"))
            continue
        sid = step.get("id")
        if not sid:
            errors.append(_err(f"steps[{i}].id", "step needs an id"))
        elif sid in seen:
            errors.append(_err(f"steps[{i}].id", f"duplicate step id {sid!r}"))
        else:
            seen.add(sid)
        if not step.get("goal"):
            errors.append(_err(f"steps[{i}].goal", "step needs a goal"))
        # done_when is what makes a step checkable rather than aspirational —
        # without it the executor cannot know when to stop and QA cannot judge.
        if not step.get("done_when"):
            errors.append(
                _err(f"steps[{i}].done_when", "step needs a verifiable completion condition")
            )
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        for dep in step.get("depends_on") or []:
            if dep not in seen:
                errors.append(_err(f"steps[{i}].depends_on", f"unknown step id {dep!r}"))


def _validate_changes(changes: Any, errors: list[EnvelopeError]) -> None:
    if not isinstance(changes, list):
        errors.append(_err("changes", "executor must return a list of changes (may be empty)"))
        return
    for i, change in enumerate(changes):
        if not isinstance(change, dict):
            errors.append(_err(f"changes[{i}]", "each change must be an object"))
            continue
        if not change.get("path"):
            errors.append(_err(f"changes[{i}].path", "change needs a path"))
        if not change.get("why"):
            errors.append(_err(f"changes[{i}].why", "change needs a reason (the diff shows what)"))


def _validate_qa(envelope: dict[str, Any], errors: list[EnvelopeError]) -> None:
    verdict = envelope.get("verdict")
    if verdict not in ("approved", "rejected"):
        errors.append(_err("verdict", "qa verdict must be 'approved' or 'rejected'"))
    findings = envelope.get("findings")
    if not isinstance(findings, list):
        errors.append(_err("findings", "qa must return a findings list (may be empty)"))
        return
    for i, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(_err(f"findings[{i}]", "each finding must be an object"))
            continue
        if finding.get("severity") not in SEVERITIES:
            errors.append(
                _err(f"findings[{i}].severity", f"severity must be one of {', '.join(SEVERITIES)}")
            )
        if not finding.get("claim"):
            errors.append(_err(f"findings[{i}].claim", "finding needs a claim"))
        # A finding without evidence is an opinion. QA exists to be objective
        # across runs, so every finding has to point at something checkable.
        if not finding.get("evidence"):
            errors.append(_err(f"findings[{i}].evidence", "finding needs evidence"))
    if verdict == "rejected" and not findings:
        errors.append(_err("findings", "a rejected verdict must say what is wrong"))
    if verdict == "approved" and any(
        isinstance(f, dict) and f.get("severity") == "P0" for f in findings
    ):
        errors.append(_err("verdict", "cannot approve while a P0 finding stands"))


def validate_envelope(envelope: Any) -> list[EnvelopeError]:
    """Return a list of contract violations. Empty list means valid.

    Returns errors rather than raising: the caller is a CLI that reports every
    problem at once, because an agent fixing one field at a time across
    round-trips is the slowest possible way to converge.
    """
    errors: list[EnvelopeError] = []
    if not isinstance(envelope, dict):
        return [_err("", "envelope must be a JSON object")]

    for field in _COMMON_REQUIRED:
        if field not in envelope or envelope[field] in (None, ""):
            errors.append(_err(field, "required field is missing or empty"))

    if envelope.get("schema") not in (None, "", SCHEMA_ID):
        errors.append(_err("schema", f"expected {SCHEMA_ID!r}, got {envelope.get('schema')!r}"))

    role = envelope.get("role")
    if role not in ROLES:
        errors.append(_err("role", f"role must be one of {', '.join(ROLES)}"))

    status = envelope.get("status")
    if status not in STATUSES:
        errors.append(_err("status", f"status must be one of {', '.join(STATUSES)}"))

    next_role = envelope.get("next_role")
    if role in TRANSITIONS and next_role is not None:
        allowed = TRANSITIONS[role]
        if next_role not in allowed:
            errors.append(
                _err("next_role", f"{role} may only hand to {' or '.join(allowed)}, not {next_role!r}")
            )

    if role in _ROLE_REQUIRED:
        for field in _ROLE_REQUIRED[role]:
            if field not in envelope:
                errors.append(_err(field, f"{role} envelopes must include {field!r}"))

    if role == "planner" and "steps" in envelope:
        _validate_steps(envelope["steps"], errors)
    if role == "executor" and "changes" in envelope:
        _validate_changes(envelope["changes"], errors)
    if role == "qa":
        _validate_qa(envelope, errors)

    # The anti-hallucination rule, applied to the chain rather than to metrics:
    # claiming success obliges you to say what makes it checkable.
    evidence = envelope.get("evidence")
    if status == "ok" and not evidence:
        errors.append(_err("evidence", "status 'ok' requires at least one piece of evidence"))
    if evidence is not None and not isinstance(evidence, list):
        errors.append(_err("evidence", "evidence must be a list of strings"))

    if status == "blocked" and not envelope.get("blocked_on"):
        errors.append(_err("blocked_on", "status 'blocked' must say what it is blocked on"))

    return errors


def load_envelope(source: str) -> tuple[Any, list[EnvelopeError]]:
    """Read an envelope from a file path, or parse it as a literal JSON string.

    Returns (envelope, errors). A parse failure is reported the same way a
    contract violation is, so callers have one error path instead of two.
    """
    text = source
    if os.path.exists(source):
        try:
            with open(source, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as exc:
            get_local_logger().warning("load_envelope: cannot read %s: %s", source, exc)
            return None, [_err("", f"cannot read {source}: {exc}")]
    try:
        return json.loads(text), []
    except json.JSONDecodeError as exc:
        return None, [_err("", f"not valid JSON: {exc}")]


def next_step(envelope: dict[str, Any]) -> str:
    """Return the routing decision a caller should act on: a role, or 'none'.

    Routing is derived from the envelope rather than decided by the caller, so
    every consumer of a valid envelope routes it identically.
    """
    if envelope.get("status") in ("blocked", "failed"):
        return "none"
    return envelope.get("next_role") or "none"


def role_versions(config: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (role, version) for every configured agent role.

    Role prompts are versioned like code (see skills/pipeline/SKILL.md); an
    unversioned role is reported as "unversioned" so it shows up as a gap
    rather than silently passing.
    """
    agents = config.get("agents") or {}
    if not isinstance(agents, dict):
        return []
    return sorted(
        (name, (spec.get("version") if isinstance(spec, dict) else None) or "unversioned")
        for name, spec in agents.items()
    )
