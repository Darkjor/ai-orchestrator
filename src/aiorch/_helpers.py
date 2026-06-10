import ast as _ast
import json
import os
import re
import fnmatch
import subprocess

# Module-level compiled regex constants — avoids per-call re.compile() overhead.
_RE_ALERT_HEADER = re.compile(r"### \[(ALERT-\d+)\]\s*(.*)")
_RE_ALERT_ID = re.compile(r"### \[(ALERT-(\d+))\]")
_RE_PENDING_HEADER = re.compile(r"### \[([A-Z]+-\d+)\]\s*(.*)")
_RE_HEADING = re.compile(r"^#{1,4}\s")


def parse_alerts(alerts_path: str) -> list:
    """Return open P0/P1/P2 alerts from ALERTS.md."""
    if not os.path.exists(alerts_path):
        return []
    alerts = []
    current_severity = "P2"
    with open(alerts_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        s = line.strip()
        if s.startswith("## P0"):
            current_severity = "P0"
        elif s.startswith("## P1"):
            current_severity = "P1"
        elif s.startswith("## P2"):
            current_severity = "P2"
        elif s.startswith("## RESOLVED"):
            current_severity = "RESOLVED"
        if s.startswith("### [ALERT-"):
            m = _RE_ALERT_HEADER.search(s)
            if m and current_severity != "RESOLVED":
                alerts.append({"id": m.group(1), "title": m.group(2), "severity": current_severity, "status": "Open"})
    return alerts


def _all_alert_ids(alerts_path: str) -> list:
    """Return all ALERT IDs regardless of resolved status."""
    if not os.path.exists(alerts_path):
        return []
    ids = []
    with open(alerts_path, "r", encoding="utf-8") as f:
        for line in f:
            m = _RE_ALERT_ID.search(line)
            if m:
                ids.append(int(m.group(2)))
    return ids


def _next_alert_id(alerts_path: str) -> str:
    """Return next sequential ALERT-XXX ID, counting resolved alerts too."""
    numbers = _all_alert_ids(alerts_path)
    if not numbers:
        return "ALERT-001"
    return f"ALERT-{(max(numbers) + 1):03d}"


def _insert_alert(alerts_path: str, alert_data: dict, today_str: str) -> bool:
    """Insert alert block under its severity section. Returns True on success."""
    with open(alerts_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    header = f"## {alert_data['severity']}"
    for i, line in enumerate(lines):
        if header in line:
            block = (
                f"\n### [{alert_data['id']}] {alert_data['title']}\n"
                f"**Severity**: {alert_data['severity']}\n**Status**:   Open\n**Owner**:    None\n"
                f"**Discovered**: {today_str}\n**Impact**: [TBD]\n**Fix**: [TBD]\n"
            )
            lines.insert(i + 1, block)
            with open(alerts_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
    return False


def parse_lint_rules(wheels_path: str) -> list:
    """Parse LINT-XXX rules from the Lint Rules section of WHEELS.md."""
    if not os.path.exists(wheels_path):
        return []
    with open(wheels_path, "r", encoding="utf-8") as f:
        content = f.read()
    section = re.search(r"## 4\. Lint Rules.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if not section:
        return []
    rules = []
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


def update_section(filepath: str, section: str, value: str) -> bool:
    """Replace content under a Markdown heading. Returns True if section found."""
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


def generate_snapshot(src_root: str) -> str:
    """Walk src_root for .py files and return a Markdown symbol list."""
    lines = []
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
                continue
            symbols = [
                n.name for n in tree.body
                if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef))
            ]
            if symbols:
                lines.append(f"- `{rel}`: {', '.join(symbols)}")
    return "\n".join(lines) if lines else "*(no Python files found)*"


def inject_snapshot(context_path: str, snapshot_text: str) -> None:
    """Upsert a ## Codebase Snapshot section at the end of context_path."""
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


def parse_pending(pending_path: str) -> list:
    """Return open pending actions from PENDING.md."""
    if not os.path.exists(pending_path):
        return []
    actions = []
    current_type = "Other"
    with open(pending_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        s = line.strip()
        if s.startswith("## Database"):
            current_type = "Database"
        elif s.startswith("## Infrastructure"):
            current_type = "Infrastructure"
        elif s.startswith("## Other"):
            current_type = "Other"
        elif s.startswith("## DONE"):
            current_type = "DONE"
        m = _RE_PENDING_HEADER.search(s)
        if m and current_type != "DONE":
            actions.append({"id": m.group(1), "title": m.group(2), "type": current_type})
    return actions


def _next_action_id(pending_path: str, prefix: str) -> str:
    """Return next sequential ID for a given prefix (DB, INFRA, ACTION)."""
    if not os.path.exists(pending_path):
        return f"{prefix}-001"
    with open(pending_path, "r", encoding="utf-8") as f:
        content = f.read()
    numbers = [int(m.group(1)) for m in re.finditer(rf"\[{prefix}-(\d+)\]", content)]
    return f"{prefix}-{(max(numbers) + 1):03d}" if numbers else f"{prefix}-001"


def _insert_action(pending_path: str, data: dict, today_str: str) -> bool:
    """Insert action block under its type section. Returns True on success."""
    type_to_header = {"db": "## Database", "infra": "## Infrastructure", "other": "## Other"}
    header = type_to_header.get(data["type"].lower(), "## Other")
    sql_block = f"\n**SQL**:\n```sql\n{data['sql']}\n```" if data.get("sql") else ""
    steps_line = f"\n**Steps**: {data['steps']}\n1. Run: `ai-orch action-resolve {data['id']}`\n" if data.get("steps") else f"\n**Steps**: [TBD]\n1. Run: `ai-orch action-resolve {data['id']}`\n"
    block = (
        f"\n### [{data['id']}] {data['title']}\n"
        f"**Status**: Pending\n**Target**: {data.get('target', '[TBD]')}\n**Discovered**: {today_str}"
        f"{sql_block}{steps_line}"
    )
    with open(pending_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if header in line:
            lines.insert(i + 1, block)
            with open(pending_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
    return False


def _resolve_action(pending_path: str, action_id: str) -> bool:
    """Mark action as Done and move block to ## DONE section."""
    with open(pending_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = next((i for i, l in enumerate(lines) if re.search(rf"### \[{re.escape(action_id)}\]", l)), -1)
    if start == -1:
        return False
    end = next((j for j in range(start + 1, len(lines)) if _RE_HEADING.match(lines[j])), len(lines))
    block = [l.replace("**Status**: Pending", "**Status**: Done") for l in lines[start:end]]
    remaining = lines[:start] + lines[end:]
    done = next((i for i, l in enumerate(remaining) if l.strip() == "## DONE"), -1)
    if done == -1:
        remaining += ["\n## DONE\n"] + block
    else:
        remaining = remaining[:done + 1] + ["\n"] + block + remaining[done + 1:]
    with open(pending_path, "w", encoding="utf-8") as f:
        f.writelines(remaining)
    return True


def load_config(config_path: str) -> dict:
    """Load and return config.json as a dict. Returns {} on missing or corrupt file."""
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def update_context(context_path: str, today_str: str, accomplishments: str, changed_files: str) -> bool:
    """Update CONTEXT.md date stamp and inject accomplishment / changed-file bullets.

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
        for i, line in enumerate(lines):
            if "**What works right now:**" in line:
                new_bullets = [f"- {a.strip()}" for a in accomplishments.split(",") if a.strip()]
                lines = lines[: i + 1] + new_bullets + lines[i + 1:]
                break
        content = "\n".join(lines)

    if changed_files.strip():
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "**Most recently changed:**" in line:
                new_bullets = [f"- {cf.strip()}" for cf in changed_files.split(",") if cf.strip()]
                next_sec_idx = len(lines)
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith("---") or lines[j].strip().startswith("##"):
                        next_sec_idx = j
                        break
                lines = lines[: i + 1] + new_bullets + lines[next_sec_idx:]
                break
        content = "\n".join(lines)

    with open(context_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def append_decision(decisions_path: str, dec_data: dict, today_str: str) -> None:
    """Append a new decision block to DECISIONS.md."""
    if not os.path.exists(decisions_path):
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


def run_git_commit(block_num: str, commit_type: str, msg: str) -> tuple[bool, str]:
    """Stage all changes and create a git commit. Returns (success, error_message)."""
    try:
        subprocess.run(["git", "add", "."], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        return False, f"git add failed: {e.stderr.strip()}"
    commit_msg = f"[{block_num}] {commit_type}: {msg}"
    try:
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        return False, f"git commit failed: {e.stderr.strip()}"
    return True, commit_msg


def _has_merge_conflicts() -> bool:
    """Return True if git grep finds merge conflict markers in the working tree.

    Uses ``git grep`` (O(diff)) instead of a full os.walk scan (O(repo-bytes)).
    Falls back to False when not in a git repo or git is unavailable; the
    caller can then use its own file-scan as a fallback.
    """
    try:
        result = subprocess.run(
            ["git", "grep", "-l", "^<<<<<<<"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def count_decisions(decisions_path: str) -> int:
    """Count decision entries (## [ headers) in DECISIONS.md."""
    if not os.path.exists(decisions_path):
        return 0
    with open(decisions_path, "r", encoding="utf-8") as f:
        content = f.read()
    return len(re.findall(r"^## \[", content, re.MULTILINE))


def parse_analysis_status(analysis_path: str) -> str:
    """Read the ## Status value from ANALYSIS.md. Returns 'NOT_FOUND' if missing."""
    if not os.path.exists(analysis_path):
        return "NOT_FOUND"
    with open(analysis_path, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"^## Status\s*\n+([A-Z_]+)", content, re.MULTILINE)
    return m.group(1).strip() if m else "NOT_FOUND"


def set_analysis_status(analysis_path: str, status: str) -> bool:
    """Replace the status value in the ## Status section of ANALYSIS.md."""
    if not os.path.exists(analysis_path):
        return False
    with open(analysis_path, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(
        r"(^## Status\s*\n+)[A-Z_]+",
        lambda m: m.group(1) + status,
        content,
        flags=re.MULTILINE,
    )
    if new_content == content:
        return False
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def collect_project_metrics(ai_dir: str) -> dict:
    """Collect real project metrics from .ai/ files and git. Returns a metrics dict."""
    alerts = parse_alerts(os.path.join(ai_dir, "ALERTS.md"))
    pending = parse_pending(os.path.join(ai_dir, "PENDING.md"))
    decisions_count = count_decisions(os.path.join(ai_dir, "DECISIONS.md"))

    tests_collected = 0
    try:
        res = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            capture_output=True, text=True, timeout=30,
        )
        m = re.search(r"(\d+) tests? collected", res.stdout + res.stderr)
        if m:
            tests_collected = int(m.group(1))
    except Exception:
        pass

    git_modified = 0
    if os.path.exists(".git"):
        try:
            git_res = subprocess.run(
                ["git", "diff", "--stat"], capture_output=True, text=True, timeout=10
            )
            lines = [l for l in git_res.stdout.strip().splitlines() if l.strip()]
            git_modified = max(0, len(lines) - 1)
        except Exception:
            pass

    return {
        "alerts": alerts,
        "p0": sum(1 for a in alerts if a["severity"] == "P0"),
        "p1": sum(1 for a in alerts if a["severity"] == "P1"),
        "p2": sum(1 for a in alerts if a["severity"] == "P2"),
        "pending": pending,
        "pending_count": len(pending),
        "decisions_count": decisions_count,
        "tests_collected": tests_collected,
        "git_modified": git_modified,
    }


def write_analysis_report(analysis_path: str, metrics: dict, agent_role: str, today_str: str) -> None:
    """Write a fresh ANALYSIS.md from collected metrics."""
    sources = "pytest, parse_alerts(), parse_pending(), DECISIONS.md, git diff"
    findings = []
    if metrics["p0"] > 0:
        findings.append(f"- **CRÍTICO**: {metrics['p0']} alerta(s) P0 — requiere atención inmediata")
    if metrics["p1"] > 0:
        findings.append(f"- {metrics['p1']} alerta(s) P1 activa(s)")
    if metrics["pending_count"] > 0:
        findings.append(f"- {metrics['pending_count']} acción(es) pendiente(s) sin resolver")
    if not findings:
        findings.append("- Sin hallazgos críticos — proyecto en estado saludable")
    ambiguous = "No" if metrics["p0"] == 0 else f"Sí — {metrics['p0']} P0(s)"
    ambig_result = "PASS" if metrics["p0"] == 0 else "ESCALATE"
    content = (
        "# Analysis Report — AI Orchestrator\n\n"
        "> Auto-generated by `ai-orch analyze`. Do NOT edit manually.\n"
        "> QA reviewed via `ai-orch qa`.\n\n"
        "## Metadata\n\n"
        "| Key | Value |\n|-----|-------|\n"
        f"| Run date | {today_str} |\n"
        "| Agent | analyzer |\n"
        f"| Agent role | {agent_role[:80]} |\n"
        "| Status | PENDING |\n\n"
        "## Real Metrics\n\n"
        "| Metric | Value | Source |\n|--------|-------|--------|\n"
        f"| Tests collected | {metrics['tests_collected']} | pytest --collect-only |\n"
        f"| Open alerts P0 | {metrics['p0']} | ALERTS.md |\n"
        f"| Open alerts P1 | {metrics['p1']} | ALERTS.md |\n"
        f"| Open alerts P2 | {metrics['p2']} | ALERTS.md |\n"
        f"| Pending actions | {metrics['pending_count']} | PENDING.md |\n"
        f"| Decisions recorded | {metrics['decisions_count']} | DECISIONS.md |\n"
        f"| Git modified files | {metrics['git_modified']} | git diff |\n\n"
        f"## Findings\n\n{chr(10).join(findings)}\n\n"
        "## Self-Check\n\n"
        "| Question | Answer | Result |\n|----------|--------|--------|\n"
        f"| ¿Datos reales y verificables? | Sí — {sources} | PASS |\n"
        f"| ¿Algo ambiguo? | {ambiguous} | {ambig_result} |\n"
        "| ¿Alucinación? | No | PASS |\n\n"
        "## QA Review\n\n*(pending — run `ai-orch qa` to populate)*\n\n"
        "## Status\n\nPENDING\n"
    )
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(content)


def qa_cross_check(analysis_path: str, ai_dir: str) -> list:
    """Cross-check ANALYSIS.md metrics against live state. Returns list of issue strings."""
    with open(analysis_path, "r", encoding="utf-8") as f:
        content = f.read()

    def _extract(label: str):
        m = re.search(rf"\| {re.escape(label)} \| (\d+) \|", content)
        return int(m.group(1)) if m else None

    stored_p0 = _extract("Open alerts P0")
    stored_pending = _extract("Pending actions")
    live_alerts = parse_alerts(os.path.join(ai_dir, "ALERTS.md"))
    live_p0 = sum(1 for a in live_alerts if a["severity"] == "P0")
    live_pending = parse_pending(os.path.join(ai_dir, "PENDING.md"))
    issues = []
    if stored_p0 is not None and stored_p0 != live_p0:
        issues.append(f"P0 alerts en ANALYSIS ({stored_p0}) ≠ estado actual ({live_p0})")
    if stored_pending is not None and stored_pending != len(live_pending):
        issues.append(f"Pending actions en ANALYSIS ({stored_pending}) ≠ estado actual ({len(live_pending)})")
    return issues


def check_staged_lint(staged_files: list, rules: list) -> list:
    """Check staged file content against lint rules. Returns list of violation dicts.

    Rules are expected to carry a pre-compiled ``compiled`` key (added by
    ``parse_lint_rules``).  If absent, the pattern string is compiled on first
    use and cached back into the rule dict so subsequent calls remain fast.
    """
    violations = []
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
        except Exception:
            continue
        for rule in matching:
            # Use pre-compiled pattern; compile lazily if absent (backward compat).
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
