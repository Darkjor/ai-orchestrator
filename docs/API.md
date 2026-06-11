# AI Orchestrator API Documentation

This guide covers programmatic usage of `ai-orch` in Python scripts and custom extensions.

## Installation

```bash
pip install ai-orchestrator
```

## Helper Functions

All helper functions are located in `aiorch._helpers`. Import them directly:

```python
from aiorch._helpers import (
    parse_alerts,
    parse_pending,
    parse_lint_rules,
    update_section,
    generate_snapshot,
    inject_snapshot,
)
```

### Alert Management

#### `parse_alerts(alerts_path: str) -> list`

Parse open (non-resolved) P0/P1/P2 alerts from `.ai/ALERTS.md`.

**Returns:** List of alert dicts with keys: `id`, `title`, `severity`, `status`

```python
from aiorch._helpers import parse_alerts

alerts = parse_alerts(".ai/ALERTS.md")
for alert in alerts:
    print(f"{alert['id']}: {alert['title']}")
    print(f"  Severity: {alert['severity']}")
    print(f"  Status: {alert['status']}")
```

**Output:**
```
ALERT-001: Missing JWT refresh logic
  Severity: P0
  Status: Open
ALERT-003: Optimize database queries
  Severity: P2
  Status: Open
```

---

### Pending Actions

#### `parse_pending(pending_path: str) -> list`

Parse open (non-done) pending manual actions from `.ai/PENDING.md`.

**Returns:** List of action dicts with keys: `id`, `title`, `type` (Database, Infrastructure, Other)

```python
from aiorch._helpers import parse_pending

actions = parse_pending(".ai/PENDING.md")
for action in actions:
    print(f"{action['id']} [{action['type']}]: {action['title']}")
```

**Output:**
```
DB-001 [Database]: Create users table
INFRA-001 [Infrastructure]: Scale Redis cluster
```

---

### Context Management

#### `update_section(filepath: str, section: str, value: str) -> bool`

Replace content under a Markdown heading (non-interactive).

**Args:**
- `filepath`: Path to the `.ai/` file (e.g., `.ai/CONTEXT.md`)
- `section`: Heading name to match (e.g., `"Current State"`)
- `value`: New content (newlines as literal `\n` strings)

**Returns:** `True` if section found and updated, `False` otherwise

```python
from aiorch._helpers import update_section

# Update Current State section
updated = update_section(
    ".ai/CONTEXT.md",
    "Current State",
    "- Fixed JWT token validation\n- Deployed to staging"
)

if not updated:
    print("Section not found in CONTEXT.md")
```

**Note:** Use `\n` in the string; it will be converted to actual newlines:

```python
# This works:
update_section(".ai/CONTEXT.md", "Current State", "- Line 1\n- Line 2")

# This does NOT work (literal backslash-n):
update_section(".ai/CONTEXT.md", "Current State", "- Line 1\n- Line 2")
```

---

### Codebase Snapshots

#### `generate_snapshot(src_root: str) -> str`

Scan a source directory and generate a Markdown symbol index (Python files only).

**Args:**
- `src_root`: Path to scan (e.g., `"src"`, `"lib"`)

**Returns:** Markdown-formatted list of modules and their top-level symbols

```python
from aiorch._helpers import generate_snapshot

snapshot = generate_snapshot("src")
print(snapshot)
```

**Output:**
```
- `src/auth.py`: authenticate, TokenManager, RefreshToken
- `src/db.py`: Database, Session, migrate_schema
- `src/api.py`: app, router
```

---

#### `inject_snapshot(context_path: str, snapshot_text: str) -> None`

Insert or update a "## Codebase Snapshot" section in `.ai/CONTEXT.md`.

**Args:**
- `context_path`: Path to `.ai/CONTEXT.md`
- `snapshot_text`: Output from `generate_snapshot()`

```python
from aiorch._helpers import generate_snapshot, inject_snapshot

snapshot = generate_snapshot("src")
inject_snapshot(".ai/CONTEXT.md", snapshot)
```

This is useful in automated workflows to keep documentation in sync:

```python
# Workflow: Scan before every commit
import subprocess
from aiorch._helpers import generate_snapshot, inject_snapshot

snapshot = generate_snapshot("src")
inject_snapshot(".ai/CONTEXT.md", snapshot)

# Now commit with updated snapshot
subprocess.run(["git", "add", ".ai/CONTEXT.md"], check=True)
```

---

### Lint Rules

#### `parse_lint_rules(wheels_path: str) -> list`

Parse enforced lint rules from `.ai/WHEELS.md`.

**Returns:** List of rule dicts with keys: `pattern` (regex), `files` (glob list), `message`

```python
from aiorch._helpers import parse_lint_rules

rules = parse_lint_rules(".ai/WHEELS.md")
for rule in rules:
    print(f"Pattern: {rule['pattern']}")
    print(f"Files: {rule['files']}")
    print(f"Message: {rule['message']}")
```

Lint rules are defined in `.ai/WHEELS.md` under section `## 4. Lint Rules`:

```markdown
## 4. Lint Rules (enforced at pre-commit)

### [LINT-001] No debug logs
**Pattern**: `console\.log\(`
**Files**: *.js, *.ts
**Message**: Remove console.log before committing.
```

---

## Extending with Custom Commands

Add custom Typer commands to the CLI by extending `main.py`:

### Example: Custom project scanner

Create `src/aiorch/commands/scanner.py`:

```python
import typer
from rich.console import Console

console = Console()

def register_scanner(app: typer.Typer):
    @app.command("scan-security")
    def scan_security(
        target: str = typer.Argument("src", help="Directory to scan"),
    ):
        """Scan codebase for security issues."""
        console.print(f"[bold]Scanning {target} for security issues...[/bold]")
        # Your security scanning logic here
        console.print("[green][OK] No high-risk patterns found.[/green]")
```

Then import and register in `main.py`:

```python
from aiorch.commands.scanner import register_scanner

# ... after app = typer.Typer() ...
register_scanner(app)
```

Now your command is available:

```bash
ai-orch scan-security
ai-orch scan-security --target lib/
```

---

## Integration Examples

### Example 1: Pre-commit automation

Check alerts and abort commit if P0 exists:

```python
#!/usr/bin/env python3
# scripts/pre-commit-check.py
import sys
from aiorch._helpers import parse_alerts

alerts = parse_alerts(".ai/ALERTS.md")
p0_alerts = [a for a in alerts if a["severity"] == "P0"]

if p0_alerts:
    print("ABORT: P0 alert(s) exist:")
    for alert in p0_alerts:
        print(f"  - {alert['id']}: {alert['title']}")
    sys.exit(1)

print("OK: No P0 alerts. Safe to commit.")
```

Then call from `.git/hooks/pre-commit`:

```bash
python3 scripts/pre-commit-check.py && ai-orch check
```

---

### Example 2: CI/CD status report

Generate a status report for GitHub Actions:

```python
#!/usr/bin/env python3
# scripts/ci-status.py
import json
from aiorch._helpers import parse_alerts, parse_pending

alerts = parse_alerts(".ai/ALERTS.md")
actions = parse_pending(".ai/PENDING.md")

status = {
    "alert_count": len(alerts),
    "p0_count": len([a for a in alerts if a["severity"] == "P0"]),
    "pending_actions": len(actions),
    "alerts": [{"id": a["id"], "severity": a["severity"]} for a in alerts],
}

print(json.dumps(status, indent=2))
```

Usage in CI:

```yaml
- name: Project Health Check
  run: |
    status=$(python3 scripts/ci-status.py)
    echo "Project Status:" 
    echo "$status"
```

---

### Example 3: Automated documentation sync

Update codebase snapshot on every build:

```python
#!/usr/bin/env python3
# scripts/update-snapshot.py
import sys
import subprocess
from aiorch._helpers import generate_snapshot, inject_snapshot

# Generate fresh snapshot
snapshot = generate_snapshot("src")
inject_snapshot(".ai/CONTEXT.md", snapshot)

# Auto-commit if changed
result = subprocess.run(["git", "diff", "--quiet", ".ai/CONTEXT.md"])
if result.returncode != 0:  # File changed
    subprocess.run(["git", "add", ".ai/CONTEXT.md"], check=True)
    subprocess.run(
        ["git", "commit", "-m", "docs: update codebase snapshot"],
        check=True
    )
    print("Updated CONTEXT.md snapshot")
else:
    print("No snapshot changes")
```

---

## File Format Reference

### `.ai/ALERTS.md` structure

```markdown
# Active Alerts

## P0 — Blocking

### [ALERT-001] Critical bug in production
**Severity**: P0
**Status**: Open
**Owner**: None
**Discovered**: 2024-01-15
**Impact**: Users cannot log in
**Fix**: [TBD]

## P1 — Important

### [ALERT-002] Performance regression
**Severity**: P1
**Status**: Open
...

## P2 — Noted

*(none)*

## RESOLVED

### [ALERT-001] Missing JWT refresh logic
**Status**: Resolved
...
```

Alerts are considered "open" if they appear before the `## RESOLVED` section.

---

### `.ai/CONTEXT.md` structure

```markdown
# Project Context

## Current State (updated: 2024-01-20)

**What works right now:**
- User authentication with JWT
- Basic CRUD operations

**Most recently changed:**
- src/auth.py: Added refresh token logic
- src/db.py: Optimized query performance

## Architecture Overview

[Project-specific details]

## Codebase Snapshot

- `src/auth.py`: authenticate, TokenManager
- `src/db.py`: Database, Session
```

---

### `.ai/PENDING.md` structure

```markdown
# Pending Manual Actions

## Database

### [DB-001] Create users table
**Status**: Pending
**Target**: PostgreSQL production
**Discovered**: 2024-01-15
**SQL**:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Steps**: 
1. Run the SQL above in Supabase
2. Run: `ai-orch action-resolve DB-001`

## Infrastructure

### [INFRA-001] Scale Redis cluster
**Status**: Pending
**Target**: AWS ElastiCache
**Steps**:
1. Increase node count from 2 to 4
2. Run: `ai-orch action-resolve INFRA-001`

## Other

*(none)*

## DONE

### [DB-001] Migrate user sessions table
**Status**: Done
```

---

## Testing

Test your extensions and integrations with pytest:

```python
# tests/test_custom.py
import tempfile
import os
from aiorch._helpers import parse_alerts

def test_parse_alerts_custom():
    alerts_md = """
# Alerts
## P0 — Blocking
### [ALERT-001] Test alert
**Severity**: P0
**Status**: Open
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(alerts_md)
        f.flush()
        alerts = parse_alerts(f.name)
    
    assert len(alerts) == 1
    assert alerts[0]["id"] == "ALERT-001"
    
    os.unlink(f.name)
```

Run tests:

```bash
pytest tests/test_custom.py -v
```

---

## Performance Notes

- `parse_alerts()` and `parse_pending()` are O(n) where n = lines in file
- `generate_snapshot()` walks the file system; exclude large directories via `.gitignore`
- `update_section()` reads and rewrites the entire file; use sparingly in tight loops

For large projects (10k+ Python files), consider using async wrappers or caching snapshots.

---

## Error Handling

All functions are safe to call with missing/invalid files:

```python
from aiorch._helpers import parse_alerts

# Returns empty list if file doesn't exist
alerts = parse_alerts(".ai/ALERTS.md")
print(len(alerts))  # Output: 0
```

For strict validation, check existence first:

```python
import os
from aiorch._helpers import parse_alerts

if not os.path.exists(".ai/ALERTS.md"):
    raise FileNotFoundError("Run 'ai-orch init' first")

alerts = parse_alerts(".ai/ALERTS.md")
```

---

## Contributing

To add a new helper function:

1. Add function to `src/aiorch/_helpers.py`
2. Add tests to `tests/test_cli.py`
3. Document it in this API guide
4. Submit a PR

See the [GitHub repository](https://github.com/yourorg/ai-orchestrator) for contribution guidelines.
