"""Exposing the .ai/ folder to audiences that never run the CLI.

WHY this module exists: `.ai/` is written for agents that can call `ai-orch`.
Two audiences can't:

1. **Humans browsing the repo in an IDE.** They see a folder of Markdown files
   with positional-severity conventions and no entry point. `render_brief`
   flattens the live state into one page that reads top-to-bottom in any
   Markdown preview.
2. **Agents in IDEs with no ai-orch plugin** — Antigravity, Cursor, Copilot.
   They read conventional context files instead. `AGENTS_MD_BLOCK` and
   `ANTIGRAVITY_RULE` teach the protocol through those files, so the folder
   works without anything installed.

Like analysis.py, this module aggregates sibling domain modules (alerts,
pending, decisions, context, config) — it is a reader, never a parser, and
must not grow its own Markdown format rules.

Managed-block contract: generated content sits between MANAGED_START and
MANAGED_END so a regeneration replaces only our block and never a line the
user wrote. Losing someone's hand-written AGENTS.md would be unforgivable for
a tool whose entire premise is not losing context.
"""
from __future__ import annotations

import os
from typing import Any

from aiorch.alerts import parse_alerts
from aiorch.context import read_section
from aiorch.decisions import count_decisions
from aiorch.logs import get_local_logger
from aiorch.pending import parse_pending

MANAGED_START = "<!-- ai-orch:start -->"
MANAGED_END = "<!-- ai-orch:end -->"

# Written into AGENTS.md — the cross-tool convention Antigravity (1.20.5+),
# Cursor and Copilot read automatically. Kept short on purpose: it is loaded
# into every session, so it points at the folder rather than restating it.
AGENTS_MD_BLOCK = """## Project context lives in `.ai/`

This repository uses [ai-orch](https://github.com/Darkjor/ai-orchestrator) to
carry context across sessions. Before doing anything else:

1. Read `.ai/CONTEXT.md` — what works, what is broken, where the last session stopped.
2. Read `.ai/ALERTS.md` — open P0/P1/P2 issues. A P0 that touches your task is
   handled first, or you say plainly why you cannot.
3. Read `.ai/WHEELS.md` — approaches already tried and rejected. Do not
   re-litigate a `FAIL-XXX` entry without a reason it does not already answer.
4. Check `.ai/PENDING.md` — work only a human can do (migrations, credentials,
   cloud consoles). Say so before writing code that assumes it is done.

`ai-orch triage` does steps 1-4 in one command if the CLI is installed.

**Before you finish**, record what the next agent would otherwise rediscover:

```bash
ai-orch sync --note "what you did and exactly where you stopped"
```

`sync` needs no input and never prompts — it reads the changed files from git.
If the CLI is unavailable, edit `.ai/CONTEXT.md` by hand instead: update
`## Current State` and `## Most recently changed`.

Never run `ai-orch handoff` or `ai-orch qa` unattended — both block on stdin.
Never bypass the pre-commit guard with `--no-verify`; update `.ai/` instead.
"""

# Claude Code reads CLAUDE.md, and `@path` lines there are IMPORTS: the file is
# pulled into the cached project-context layer every session, instead of relying
# on an agent knowing to go Read it. This is the mechanism DEC-007 established
# (commit ce554dc, "closes that discovery gap") and that removing the repo's own
# .ai/ folder in 30693e1 silently took away without a superseding decision.
CLAUDE_MD_BLOCK = """## Project context (auto-loaded)

The files below are imported, not just referenced — Claude Code loads them into
project context every session, so the arrival protocol runs without anyone
remembering to ask for it.

@.ai/ORCHESTRATOR.md
@.ai/CONTEXT.md
@.ai/ALERTS.md
@.ai/WHEELS.md

`ai-orch triage` is the same information as a single command. Before finishing,
record the session with `ai-orch sync --note "what you did, where you stopped"`.
"""

# Antigravity workspace rule. `trigger: always_on` is that IDE's nearest
# equivalent to a SessionStart hook: it is injected into every agent turn.
ANTIGRAVITY_RULE = """---
trigger: always_on
description: >-
  Cross-session project context for this repository. Directs the agent to read
  the .ai/ folder (CONTEXT, ALERTS, WHEELS, PENDING) on arrival and to record
  state with `ai-orch sync` before finishing. Applies to every task.
---

""" + AGENTS_MD_BLOCK


def _severity_rows(alerts: list) -> list[str]:
    rows = []
    for sev in ("P0", "P1", "P2"):
        for a in alerts:
            if a["severity"] == sev:
                rows.append(f"| `{a['id']}` | **{sev}** | {a['title']} |")
    return rows


def render_brief(ai_dir: str, config: dict[str, Any], today_str: str) -> str:
    """Render the live .ai/ state as one human-readable Markdown page.

    Reading order mirrors what a person actually wants to know when they open
    an unfamiliar repo: what is this, what is happening now, what is broken,
    what is waiting on a person, and only then where the detail lives.
    """
    name = config.get("project_name") or os.path.basename(os.path.abspath(".")) or "This project"
    alerts = parse_alerts(os.path.join(ai_dir, "ALERTS.md"))
    pending = parse_pending(os.path.join(ai_dir, "PENDING.md"))
    decisions = count_decisions(os.path.join(ai_dir, "DECISIONS.md"))
    context_path = os.path.join(ai_dir, "CONTEXT.md")
    state = read_section(context_path, "Current State")
    changed = read_section(context_path, "Most recently changed")

    p0 = sum(1 for a in alerts if a["severity"] == "P0")
    p1 = sum(1 for a in alerts if a["severity"] == "P1")

    if p0:
        headline = f"**{p0} blocking issue(s).** Work here is not safe to build on until they are resolved."
    elif p1:
        headline = f"No blockers. {p1} issue(s) worth knowing about before you start."
    else:
        headline = "No open blockers."

    out = [
        f"# {name} — project status",
        "",
        f"> Generated by `ai-orch brief` on {today_str} from the `.ai/` folder.",
        "> Do not edit by hand — regenerate instead.",
        "",
        headline,
        "",
    ]

    facts = []
    if config.get("project_type"):
        facts.append(f"| Type | {config['project_type']} |")
    if config.get("stack"):
        facts.append(f"| Stack | {config['stack']} |")
    if config.get("test_command"):
        facts.append(f"| Tests | `{config['test_command']}` |")
    facts.append(f"| Open alerts | {len(alerts)} ({p0} P0, {p1} P1) |")
    facts.append(f"| Waiting on a human | {len(pending)} |")
    facts.append(f"| Decisions on record | {decisions} |")
    out += ["| | |", "|---|---|"] + facts + [""]

    out += ["## What is happening now", ""]
    out += [state if state else "*`## Current State` in `.ai/CONTEXT.md` is empty.*", ""]

    out += ["## What is broken", ""]
    if alerts:
        out += ["| ID | Severity | Issue |", "|----|----------|-------|"]
        out += _severity_rows(alerts)
    else:
        out.append("Nothing open.")
    out.append("")

    out += ["## What needs a person", ""]
    if pending:
        out += ["These cannot be done by an agent — they need someone with access.", ""]
        out += ["| ID | Type | Action |", "|----|------|--------|"]
        out += [f"| `{a['id']}` | {a['type']} | {a['title']} |" for a in pending]
        out += ["", "Close one with `ai-orch action-resolve <ID>`."]
    else:
        out.append("Nothing waiting.")
    out.append("")

    if changed:
        out += ["## Most recently changed", "", changed, ""]

    out += [
        "## Where the detail lives",
        "",
        "| File | Holds |",
        "|------|-------|",
        "| `.ai/CONTEXT.md` | Full current state and the codebase symbol map |",
        "| `.ai/ALERTS.md` | Every alert, open and resolved |",
        "| `.ai/DECISIONS.md` | Why the project is built the way it is |",
        "| `.ai/WHEELS.md` | Approaches already tried and rejected |",
        "| `.ai/PENDING.md` | Manual actions, open and done |",
        "| `.ai/DISCUSSIONS.md` | Open threads between agents |",
        "",
        "Arriving to work on this? Run `ai-orch triage`, then read `.ai/CONTEXT.md`.",
        "",
    ]
    return "\n".join(out)


def write_managed_block(path: str, block: str, title: str = "") -> str:
    """Write `block` between the managed markers in `path`, idempotently.

    Returns "created", "updated" or "unchanged". Content outside the markers is
    never touched; a file that exists without markers gets the block appended
    rather than replaced, so a hand-written AGENTS.md survives intact.
    """
    payload = f"{MANAGED_START}\n{block.rstrip()}\n{MANAGED_END}\n"
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    if not os.path.exists(path):
        head = f"# {title}\n\n" if title else ""
        with open(path, "w", encoding="utf-8") as f:
            f.write(head + payload)
        return "created"

    with open(path, "r", encoding="utf-8") as f:
        existing = f.read()

    if MANAGED_START in existing and MANAGED_END in existing:
        before = existing.split(MANAGED_START, 1)[0]
        after = existing.split(MANAGED_END, 1)[1]
        updated = before + payload.rstrip("\n") + after
        if updated == existing:
            return "unchanged"
        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)
        return "updated"

    get_local_logger().debug("write_managed_block: appending fresh block to %s", path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(existing.rstrip() + "\n\n" + payload)
    return "updated"
