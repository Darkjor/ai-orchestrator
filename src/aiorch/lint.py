"""WHEELS.md lint rules — project-specific anti-patterns enforced at commit.

WHY rules live in WHEELS.md and not a linter config: WHEELS.md is the
"failed approaches / do-not-reinvent" file that agents already read on
arrival. Encoding the hard-won lessons there as machine-checkable LINT rules
closes the loop: an agent that ignores the prose still gets blocked by the
pre-commit hook.

Rule format contract (section '## 4. Lint Rules' of WHEELS.md):
    ### [LINT-001] Human-readable name
    **Pattern**: `regex`
    **Files**: *.py, *.js        (glob against basename; defaults to *)
    **Message**: Shown to the committer.
"""
from __future__ import annotations

import fnmatch
import os
import re
import subprocess

from aiorch.logs import get_local_logger
from aiorch.models import LintRule, LintViolation


def parse_lint_rules(wheels_path: str) -> list[LintRule]:
    """Parse LINT-XXX rules from the Lint Rules section of WHEELS.md.

    Patterns are compiled here, once, because check_staged_lint runs inside
    the pre-commit hook where per-line compile cost would be felt on every
    commit.
    """
    if not os.path.exists(wheels_path):
        return []
    with open(wheels_path, "r", encoding="utf-8") as f:
        content = f.read()
    section = re.search(r"## 4\. Lint Rules.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if not section:
        return []
    rules: list[LintRule] = []
    for m in re.finditer(r"### \[LINT-\d+\][^\n]*\n(.*?)(?=### \[LINT|\Z)", section.group(1), re.DOTALL):
        body = m.group(1)
        pattern = re.search(r"\*\*Pattern\*\*: `([^`]+)`", body)
        files_field = re.search(r"\*\*Files\*\*: (.+)", body)
        message = re.search(r"\*\*Message\*\*: (.+)", body)
        if pattern and message:
            globs = [g.strip() for g in files_field.group(1).split(",")] if files_field else ["*"]
            rules.append({
                "pattern": pattern.group(1),
                "compiled": re.compile(pattern.group(1)),
                "files": globs,
                "message": message.group(1).strip(),
            })
    return rules


def check_staged_lint(staged_files: list[str], rules: list[LintRule]) -> list[LintViolation]:
    """Check STAGED content of files against lint rules.

    Reads ``git show :<path>`` (the index) instead of the working tree on
    purpose: the commit ships what is staged, and a working-tree fix that was
    never `git add`-ed must not let a bad staged version through.
    """
    violations: list[LintViolation] = []
    for filepath in staged_files:
        matching = [r for r in rules if any(fnmatch.fnmatch(os.path.basename(filepath), g) for g in r["files"])]
        if not matching:
            continue
        try:
            git_path = filepath.replace(os.sep, "/")
            result = subprocess.run(
                ["git", "show", f":{git_path}"],
                capture_output=True,
                text=True,
                check=True,
            )
            content = result.stdout
        except (subprocess.CalledProcessError, OSError) as exc:
            # Legitimate for staged deletions/renames — git show has nothing
            # to print. Log at debug so unexpected cases stay diagnosable.
            get_local_logger().debug("lint: cannot read staged %s: %s", filepath, exc)
            continue
        for rule in matching:
            # Rules from parse_lint_rules are pre-compiled; compile lazily for
            # callers that build rule dicts by hand (backward compat).
            compiled = rule.get("compiled")
            if compiled is None:
                compiled = re.compile(rule["pattern"])
                rule["compiled"] = compiled
            for lineno, line in enumerate(content.splitlines(), 1):
                if compiled.search(line):
                    violations.append({
                        "file": filepath,
                        "line": lineno,
                        "message": rule["message"],
                        "code": line.strip(),
                    })
    return violations
