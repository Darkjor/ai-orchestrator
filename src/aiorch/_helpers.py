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


def _next_alert_id(alerts_path: str) -> str:
    """Return next sequential ALERT-XXX ID."""
    existing = parse_alerts(alerts_path)
    if not existing:
        return "ALERT-001"
    numbers = [int(re.search(r"\d+", a["id"]).group()) for a in existing if re.search(r"\d+", a["id"])]
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


def check_staged_lint(staged_files: list, rules: list) -> list:
    """Check staged file content against lint rules. Returns list of violation dicts."""
    violations = []
    for filepath in staged_files:
        matching = [r for r in rules if any(fnmatch.fnmatch(os.path.basename(filepath), g) for g in r["files"])]
        if not matching:
            continue
        try:
            result = subprocess.run(["git", "show", f":{filepath}"], capture_output=True, text=True, check=True)
            content = result.stdout
        except Exception:
            continue
        for rule in matching:
            for lineno, line in enumerate(content.splitlines(), 1):
                if re.search(rule["pattern"], line):
                    violations.append({"file": filepath, "line": lineno, "message": rule["message"], "code": line.strip()})
    return violations
