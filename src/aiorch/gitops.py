"""Git subprocess wrappers shared by all CLI commands.

WHY a dedicated module: every aiorch feature that talks to git funnels through
here so that (a) failure modes are handled once, (b) agents can grep ONE file
to learn how the CLI shells out, and (c) commands never crash because git is
missing — degraded behaviour is always explicitly defined.

Error contract:
- Functions that QUERY state raise :class:`GitCommandError`, letting callers
  choose between "skip the check" (`check`) and "fall back" (`triage`).
- Functions that MUTATE state (run_git_commit) return ``(ok, detail)`` tuples
  because the CLI always reports those failures to the human verbatim.
"""
from __future__ import annotations

import os
import subprocess

from aiorch.logs import get_local_logger


class GitCommandError(RuntimeError):
    """A git subprocess failed or git is unavailable."""


# Hook scripts installed by `ai-orch hook-install`. They try the installed
# entry point first and fall back to `python -m` so the hooks survive venv
# layouts where ai-orch is importable but not on PATH.
PRE_COMMIT_HOOK = """#!/bin/sh
# AI Orchestrator pre-commit validation hook

if command -v ai-orch >/dev/null 2>&1; then
  ai-orch check
else
  python -m aiorch.main check
fi
"""

POST_COMMIT_HOOK = """#!/bin/sh
# AI Orchestrator post-commit: keep codebase snapshot fresh

if command -v ai-orch >/dev/null 2>&1; then
  ai-orch snapshot --quiet 2>/dev/null || true
else
  python -m aiorch.main snapshot --quiet 2>/dev/null || true
fi
"""

# Directories never scanned for conflict markers (vendored/generated content).
_SCAN_IGNORED_DIRS = (".git", "venv", ".venv", "node_modules", "__pycache__", ".pytest_cache")
# Only text-like files are scanned — binary files can contain marker bytes by chance.
_SCAN_TEXT_SUFFIXES = (".py", ".gd", ".go", ".js", ".ts", ".json", ".md", ".txt", ".html", ".xml", ".yml", ".yaml")

_SECRET_SUFFIXES = (".env", ".pem", ".key")


def get_staged_files() -> list[str]:
    """Return paths staged in the git index.

    Raises GitCommandError instead of returning [] on failure: callers must
    be able to distinguish "nothing staged" (fine) from "git broke" (warn).
    """
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        raise GitCommandError(str(exc)) from exc
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def has_merge_conflicts() -> bool:
    """Return True if git grep finds conflict markers in tracked files.

    Uses ``git grep`` (O(diff)) instead of an os.walk scan (O(repo-bytes)).
    Returns False when git is unavailable so callers can apply their own
    fallback (triage uses scan_conflict_files for non-git folders).
    """
    try:
        result = subprocess.run(
            ["git", "grep", "-l", "^<<<<<<<"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        get_local_logger().debug("has_merge_conflicts: git grep unavailable: %s", exc)
        return False


def scan_conflict_files(root: str = ".") -> list[str]:
    """File-walk fallback for conflict markers when there is no git repo.

    A file counts as conflicted only when it has BOTH a ``<<<<<<<`` line and a
    ``=======`` line — requiring the pair avoids false positives on Markdown
    horizontal rules and heredocs.
    """
    import re

    conflicted: list[str] = []
    for dirpath, dirs, files in os.walk(root):
        if any(ig in dirpath for ig in _SCAN_IGNORED_DIRS):
            continue
        for fname in files:
            if not fname.endswith(_SCAN_TEXT_SUFFIXES):
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError as exc:
                get_local_logger().debug("scan_conflict_files: cannot read %s: %s", fpath, exc)
                continue
            if re.search(r"^<{7}", content, re.MULTILINE) and re.search(r"^={7}$", content, re.MULTILINE):
                conflicted.append(fpath)
    return conflicted


def find_secret_files(cwd: str = ".") -> list[str]:
    """Return potential secret/credential files (staged and in cwd root).

    Heuristic, not exhaustive — the goal is to catch the common accident
    (.env / .pem / .key about to be committed), not to be a secret scanner.
    Staged files additionally match on "secret" in the name because agents
    sometimes stage things like `secrets.json`.
    """
    found: list[str] = []
    if os.path.exists(os.path.join(cwd, ".git")):
        try:
            staged = get_staged_files()
        except GitCommandError as exc:
            get_local_logger().warning("find_secret_files: staged lookup failed: %s", exc)
            staged = []
        for f in staged:
            if f.endswith(_SECRET_SUFFIXES) or "secret" in f.lower():
                found.append(f)
    for f in os.listdir(cwd):
        if f.endswith(_SECRET_SUFFIXES):
            found.append(f)
    return sorted(set(found))


def run_git_commit(block_num: str, commit_type: str, msg: str) -> tuple[bool, str]:
    """Stage everything and commit as ``[<block>] <type>: <msg>``.

    The bracketed block number is the project's session-numbering convention —
    it lets agents map commits back to handoff blocks in CONTEXT.md.
    Returns (True, commit_message) or (False, human-readable error).
    """
    try:
        subprocess.run(["git", "add", "."], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        return False, f"git add failed: {e.stderr.strip()}"
    except OSError as e:
        get_local_logger().warning("run_git_commit: git unavailable: %s", e)
        return False, f"git add failed: {e}"
    commit_msg = f"[{block_num}] {commit_type}: {msg}"
    try:
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        return False, f"git commit failed: {e.stderr.strip()}"
    except OSError as e:
        get_local_logger().warning("run_git_commit: git unavailable: %s", e)
        return False, f"git commit failed: {e}"
    return True, commit_msg


def write_git_hook(hook_dir: str, name: str, content: str) -> tuple[str, str | None]:
    """Write a hook script with LF endings and mark it executable.

    LF is forced (newline="\\n") because git on Windows still executes hooks
    through sh, which rejects CRLF shebangs. chmod failure is returned as a
    warning instead of raised: on Windows chmod is a no-op and hooks run fine.
    """
    path = os.path.join(hook_dir, name)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    try:
        os.chmod(path, 0o755)
    except OSError as exc:
        return path, str(exc)
    return path, None


def get_recent_changed_files(limit: int = 25) -> list[str]:
    """Return the files this session touched, for a non-interactive handoff.

    WHY the fallback: `ai-orch sync` is meant to run at the END of a session,
    which may be either side of a commit. Uncommitted work is the better
    answer when it exists (it is what the agent is about to hand over); once
    the agent has already committed, the working tree is clean and the last
    commit's files are the only remaining evidence of what happened.

    Raises GitCommandError so callers can distinguish "nothing changed" (an
    empty list) from "git is unavailable".
    """
    try:
        # -uall expands untracked directories to individual files; the default
        # collapses a wholly-new directory to "src/", which tells a reader far
        # less than the file names inside it.
        status = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            capture_output=True, text=True, check=True, timeout=10,
        )
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as exc:
        raise GitCommandError(str(exc)) from exc

    files: list[str] = []
    for line in status.stdout.splitlines():
        # Porcelain v1: 2 status chars, a space, then the path. Renames read
        # "R  old -> new"; the new name is the one worth reporting.
        path = line[3:].strip() if len(line) > 3 else ""
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and not path.startswith(".ai/"):
            files.append(path.strip('"'))

    if not files:
        try:
            res = subprocess.run(
                ["git", "show", "--name-only", "--pretty=format:", "HEAD"],
                capture_output=True, text=True, check=True, timeout=10,
            )
            files = [
                l.strip() for l in res.stdout.splitlines()
                if l.strip() and not l.strip().startswith(".ai/")
            ]
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as exc:
            # An empty repo has no HEAD — that is "nothing to report", not a
            # failure worth propagating.
            get_local_logger().debug("get_recent_changed_files: no HEAD: %s", exc)
            return []

    return sorted(dict.fromkeys(files))[:limit]
