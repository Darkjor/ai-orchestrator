import os
import re
import fnmatch
import subprocess


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
            m = re.search(r"### \[(ALERT-\d+)\]\s*(.*)", s)
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
            m = re.search(r"### \[(ALERT-(\d+))\]", line)
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
            rules.append({"pattern": pattern.group(1), "files": globs, "message": message.group(1).strip()})
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
        if re.match(r"^#{1,4}\s", lines[j]) or lines[j].strip() == "---":
            end_idx = j
            break
    new_value = value.replace("\\n", "\n")
    new_lines = lines[:heading_idx + 1] + ["\n", new_value + "\n", "\n"] + lines[end_idx:]
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return True


def check_staged_lint(staged_files: list, rules: list) -> list:
    """Check staged file content against lint rules. Returns list of violation dicts."""
    violations = []
    for filepath in staged_files:
        matching = [r for r in rules if any(fnmatch.fnmatch(os.path.basename(filepath), g) for g in r["files"])]
        if not matching:
            continue
        try:
            git_path = filepath.replace(os.sep, "/")
            result = subprocess.run(["git", "show", f":{git_path}"], capture_output=True, text=True, check=True)
            content = result.stdout
        except Exception:
            continue
        for rule in matching:
            for lineno, line in enumerate(content.splitlines(), 1):
                if re.search(rule["pattern"], line):
                    violations.append({"file": filepath, "line": lineno, "message": rule["message"], "code": line.strip()})
    return violations
