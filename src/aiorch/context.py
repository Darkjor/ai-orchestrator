"""Mutation of .ai/CONTEXT.md and generic section editing for any .ai/ file.

WHY section-level editing: agents update context non-interactively via
``ai-orch update --section X --value Y``. Replacing a whole Markdown section
(heading → next heading/---) is the coarsest edit that is still safe to apply
blindly — finer-grained edits would need to understand prose, coarser ones
would clobber unrelated sections.
"""
from __future__ import annotations

import ast as _ast
import os
import re

from typing import Callable, Optional

from aiorch.logs import get_local_logger

_RE_HEADING = re.compile(r"^#{1,4}\s")

# Files bundled by `ai-orch export`, in arrival-protocol reading order:
# the orchestrator manual first, then live state, then historical records.
CONTEXT_BUNDLE_FILES = [
    "ORCHESTRATOR.md",
    "CONTEXT.md",
    "ALERTS.md",
    "DECISIONS.md",
    "PENDING.md",
    "WHEELS.md",
    "DISCUSSIONS.md",
]


def update_section(filepath: str, section: str, value: str) -> bool:
    """Replace the content under a Markdown heading. Returns True if found.

    Matching is case-insensitive and prefix-based ("Current State" matches
    "## Current State (updated: ...)") because section headings carry volatile
    suffixes like dates. ``\\n`` in value is expanded to a real newline so
    agents can pass multi-line content through a single CLI argument.
    """
    if not os.path.exists(filepath):
        return False
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    heading_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip().lstrip("#").strip().lower()
        if stripped == section.lower() or stripped.startswith(section.lower()):
            heading_idx = i
            break
    if heading_idx == -1:
        return False
    end_idx = len(lines)
    for j in range(heading_idx + 1, len(lines)):
        if _RE_HEADING.match(lines[j]) or lines[j].strip() == "---":
            end_idx = j
            break
    new_value = value.replace("\\n", "\n")
    new_lines = lines[:heading_idx + 1] + ["\n", new_value + "\n", "\n"] + lines[end_idx:]
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return True


SNAPSHOT_HEADER = "## Codebase Snapshot"


def strip_snapshot(text: str) -> str:
    """Return CONTEXT.md content with the machine-generated snapshot removed.

    WHY this exists: the post-commit hook rewrites ``## Codebase Snapshot`` on
    every commit, which leaves CONTEXT.md dirty without anyone having recorded
    anything. `ai-orch check` asks "did a human or agent write context?", and
    a regenerated symbol map is not an answer to that question — staging it
    would otherwise satisfy the guard with zero real content. Comparing the
    stripped text answers the question the guard actually means to ask.
    """
    head, sep, _ = text.partition(SNAPSHOT_HEADER)
    # inject_snapshot writes "\n\n---\n\n" before the header, so the rule has
    # to go too — otherwise a file whose ONLY change is the snapshot still
    # compares as different, which is exactly the bug this function exists to
    # prevent.
    return re.sub(r"\n-{3,}[ \t]*$", "", (head if sep else text).rstrip()).rstrip()


def staged_context_records_something(staged: str | None, committed: str | None) -> bool:
    """True when a staged CONTEXT.md carries more than a regenerated snapshot.

    The commit guard means to ask "did a human or agent write context?". The
    post-commit hook rewrites ``## Codebase Snapshot`` after every commit, so
    without this a `git add -A` would stage that machine-written change and
    satisfy the guard with no real content behind it.

    Missing blobs (a first commit, a newly added file) count as real: the safe
    reading when there is nothing to compare against is that it is new.
    """
    if staged is None or committed is None:
        return True
    return strip_snapshot(staged) != strip_snapshot(committed)


# Paths the guard never counts as "code changed" — docs and packaging metadata.
_GUARD_EXEMPT_PREFIXES = (".git", "docs/")
_GUARD_EXEMPT_FILES = (".gitignore", "pyproject.toml")


def classify_staged_paths(
    staged_files: list[str],
    read_blob: Callable[[str], Optional[str]],
) -> tuple[bool, bool]:
    """Return (code_changed, context_recorded) for the commit guard.

    ``read_blob`` is injected rather than imported so this module keeps to the
    dependency rule that only the aggregator modules import siblings — and so
    the rule below is testable without a git repo.
    """
    code_changed = False
    context_recorded = False
    for f in staged_files:
        if f.startswith(".ai/"):
            # Runtime noise the tool writes about itself is never a record.
            # Projects initialized before .ai/.gitignore existed may still
            # have these tracked, so the guard rejects them here too.
            if f.startswith(".ai/logs/"):
                continue
            if f == ".ai/CONTEXT.md" and not staged_context_records_something(
                    read_blob(":.ai/CONTEXT.md"), read_blob("HEAD:.ai/CONTEXT.md")):
                continue
            context_recorded = True
        elif not f.startswith(_GUARD_EXEMPT_PREFIXES) and f not in _GUARD_EXEMPT_FILES:
            code_changed = True
    return code_changed, context_recorded


def read_section(filepath: str, section: str) -> str:
    """Return the body under a Markdown heading, or "" if absent.

    The read counterpart of update_section — same case-insensitive, prefix
    based matching, so callers that can write a section can also read it back.
    Used by `ai-orch brief` to lift the human-written state out of CONTEXT.md
    without re-implementing the heading rules.
    """
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    heading_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip().lstrip("#").strip().lower()
        if stripped == section.lower() or stripped.startswith(section.lower()):
            heading_idx = i
            break
    if heading_idx == -1:
        return ""
    end_idx = len(lines)
    for j in range(heading_idx + 1, len(lines)):
        if _RE_HEADING.match(lines[j]) or lines[j].strip() == "---":
            end_idx = j
            break
    return "".join(lines[heading_idx + 1:end_idx]).strip()


def update_context(context_path: str, today_str: str, accomplishments: str, changed_files: str) -> bool:
    """Update CONTEXT.md date stamp and inject accomplishment/changed bullets.

    New bullets are PREPENDED right under the marker lines so the most recent
    work always reads first — agents arriving at a project scan top-down and
    must hit fresh information before stale history.
    Returns True if the file was written, False if it does not exist.
    """
    if not os.path.exists(context_path):
        return False
    with open(context_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r"## Current State \(updated: [^\)]+\)",
        f"## Current State (updated: {today_str})",
        content,
    )

    if accomplishments.strip():
        lines = content.splitlines()
        found = False
        for i, line in enumerate(lines):
            if "**What works right now:**" in line:
                new_bullets = [f"- {a.strip()}" for a in accomplishments.split(",") if a.strip()]
                lines = lines[: i + 1] + new_bullets + lines[i + 1:]
                found = True
                break
        if not found:
            get_local_logger().warning(
                "update_context: marker '**What works right now:**' not found in %s — accomplishments not written",
                context_path
            )
        content = "\n".join(lines)

    if changed_files.strip():
        lines = content.splitlines()
        found = False
        for i, line in enumerate(lines):
            if "**Most recently changed:**" in line:
                new_bullets = [f"- {cf.strip()}" for cf in changed_files.split(",") if cf.strip()]
                # "Most recently changed" is replaced (not appended) — only the
                # latest session's files matter; history lives in git.
                next_sec_idx = len(lines)
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith("---") or lines[j].strip().startswith("##"):
                        next_sec_idx = j
                        break
                lines = lines[: i + 1] + new_bullets + lines[next_sec_idx:]
                found = True
                break
        if not found:
            get_local_logger().warning(
                "update_context: marker '**Most recently changed:**' not found in %s — accomplishments not written",
                context_path
            )
        content = "\n".join(lines)

    with open(context_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def generate_snapshot(src_root: str) -> str:
    """Walk src_root for .py files and return a Markdown symbol list.

    WHY AST instead of imports or grep: ast.parse never executes user code
    (safe inside git hooks) and yields exact top-level symbol names. Files
    with syntax errors are skipped silently because the snapshot runs in a
    post-commit hook and must never block or noise up a commit.
    """
    lines: list[str] = []
    for dirpath, dirs, filenames in os.walk(src_root):
        dirs.sort()
        for fname in sorted(filenames):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath).replace(os.sep, "/")
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    tree = _ast.parse(f.read(), filename=fpath)
            except SyntaxError:
                get_local_logger().debug("snapshot: skipping unparsable file %s", fpath)
                continue
            symbols = [
                n.name for n in tree.body
                if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef))
            ]
            if symbols:
                lines.append(f"- `{rel}`: {', '.join(symbols)}")
    return "\n".join(lines) if lines else "*(no Python files found)*"


def inject_snapshot(context_path: str, snapshot_text: str) -> None:
    """Upsert a ## Codebase Snapshot section at the end of CONTEXT.md.

    The snapshot is always the LAST section: it is machine-regenerated on
    every commit (post-commit hook), and keeping it at the tail means the
    regex replace can safely consume everything after the header.
    """
    if not os.path.exists(context_path):
        return
    with open(context_path, "r", encoding="utf-8") as f:
        content = f.read()
    header = "## Codebase Snapshot"
    new_section = f"{header}\n\n{snapshot_text}\n"
    if header in content:
        content = re.sub(r"## Codebase Snapshot\n.*", new_section, content, flags=re.DOTALL)
    else:
        content = content.rstrip() + "\n\n---\n\n" + new_section
    with open(context_path, "w", encoding="utf-8") as f:
        f.write(content)


def bundle_context(ai_dir: str = ".ai") -> str:
    """Concatenate all .ai/ context files into one Markdown document.

    Used by `ai-orch export` to produce a single paste-able context block for
    models that cannot browse the filesystem (web chats, API calls). Missing
    or unreadable files are skipped, not fatal — a partial bundle is still
    useful context.
    """
    sections: list[str] = []
    for filename in CONTEXT_BUNDLE_FILES:
        path = os.path.join(ai_dir, filename)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            get_local_logger().warning("export: could not read %s: %s", path, exc)
            continue
        sections.append(f"## {filename}\n---\n{content}")
    return "\n\n".join(sections)
