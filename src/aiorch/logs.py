"""Local structured logging for the aiorch CLI.

WHY: Supabase observability (aiorch.observability) is optional and remote.
Autonomous agents working inside a repo need a *local*, always-available trail
of what the CLI did and which non-fatal errors were swallowed, so they can
self-correct without network access or credentials.

Design constraints (do not relax these):
- Logging must NEVER crash the CLI — mirror of SupabaseLogger's rule.
- The log file lives at .ai/logs/aiorch.log, next to the context files agents
  already read; it is only created when a .ai/ folder exists.
- stderr only receives WARNING+ so Rich stdout output stays clean for humans
  and for tests that assert on command output.
"""
from __future__ import annotations

import logging
import os

LOG_DIR = os.path.join(".ai", "logs")
LOG_FILE = os.path.join(LOG_DIR, "aiorch.log")

_configured = False


def get_local_logger() -> logging.Logger:
    """Return the shared 'aiorch' logger, configuring handlers on first call.

    Lazy one-shot configuration (instead of module import time) because the
    CLI chdir-sensitive file handler must bind to the *current* project's
    .ai/ folder — tests and agents frequently os.chdir() before invoking
    commands.
    """
    global _configured
    logger = logging.getLogger("aiorch")
    if _configured:
        return logger

    logger.setLevel(logging.DEBUG)

    stream = logging.StreamHandler()  # stderr by default
    stream.setLevel(logging.WARNING)
    stream.setFormatter(logging.Formatter("[aiorch] %(levelname)s: %(message)s"))
    logger.addHandler(stream)

    try:
        if os.path.isdir(".ai"):
            os.makedirs(LOG_DIR, exist_ok=True)
            file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            )
            logger.addHandler(file_handler)
    except OSError:
        # Read-only filesystem or permission problem — the stderr handler
        # still works, and logging must never break the CLI.
        pass

    _configured = True
    return logger


# Written by the commands that record context (sync / update / handoff) and
# cleared by the SessionStart hook. The Stop hook reads it to answer "did
# anyone record this session?" directly, instead of inferring it from git —
# where a machine-written snapshot looks identical to a real handoff.
RECORDED_MARKER = os.path.join(LOG_DIR, ".session-recorded")


def mark_session_recorded() -> None:
    """Note that context was written this session. Never raises."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(RECORDED_MARKER, "w", encoding="utf-8") as f:
            f.write("")
    except OSError as exc:
        get_local_logger().debug("mark_session_recorded failed: %s", exc)


# `init` writes this so the runtime log and the session markers never enter
# git. Without it they show up as untracked files under .ai/, and a `git add -A`
# stages machine-written noise that then satisfies the commit guard — the guard
# would pass on a commit where nobody recorded anything.
AI_GITIGNORE = """# Runtime files written by ai-orch — never commit these.
logs/
"""


def write_ai_gitignore(ai_dir: str = ".ai") -> bool:
    """Write .ai/.gitignore unless one already exists. Never raises."""
    path = os.path.join(ai_dir, ".gitignore")
    if os.path.exists(path):
        return False
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(AI_GITIGNORE)
        return True
    except OSError as exc:
        get_local_logger().debug("write_ai_gitignore failed: %s", exc)
        return False
