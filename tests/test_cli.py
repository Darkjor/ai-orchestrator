import os
import json
import subprocess
import datetime
import pytest
from typer.testing import CliRunner
from aiorch.main import app
from aiorch._helpers import parse_lint_rules
from unittest.mock import patch, MagicMock

runner = CliRunner()

def test_init_creates_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert os.path.exists(".ai")
    assert os.path.exists(".ai/ORCHESTRATOR.md")

def test_triage_command(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    
    alerts_content = """# Active Alerts
## P0 — Blocking
### [ALERT-001] Missing virtual virtualization features
**Severity**: P0
**Status**:   Open

## P1 — Important
*(none)*

## P2 — Noted
*(none)*
"""
    with open(".ai/ALERTS.md", "w", encoding="utf-8") as f:
        f.write(alerts_content)
        
    config_path = ".ai/config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    config_data["test_command"] = "echo 'Tests run successfully'"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
        
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    assert "ALERT-001" in result.output

def test_check_command(tmp_path):
    os.chdir(tmp_path)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    runner.invoke(app, ["init"])
    
    subprocess.run(["git", "config", "user.name", "Test User"], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
    
    with open("init_file.txt", "w") as f:
        f.write("initial file")
    subprocess.run(["git", "add", "init_file.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], check=True)
    
    with open("source.py", "w") as f:
        f.write("print('hello')")
    subprocess.run(["git", "add", "source.py"], check=True)
    
    result = runner.invoke(app, ["check"])
    assert result.exit_code != 0
    
    with open(".ai/CONTEXT.md", "a") as f:
        f.write("\nUpdated context for test")
    subprocess.run(["git", "add", ".ai/CONTEXT.md"], check=True)
    
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0

def test_hook_install_command(tmp_path):
    os.chdir(tmp_path)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    runner.invoke(app, ["init"])
    
    result = runner.invoke(app, ["hook-install"])
    assert result.exit_code == 0
    
    hook_path = ".git/hooks/pre-commit"
    assert os.path.exists(hook_path)
    with open(hook_path, "r") as f:
        content = f.read()
    assert "ai-orch check" in content or "aiorch" in content

    post_hook_path = ".git/hooks/post-commit"
    assert os.path.exists(post_hook_path)
    with open(post_hook_path, "r") as f:
        post_content = f.read()
    assert "snapshot" in post_content


def test_installed_pre_commit_hook_blocks_and_allows_commit(tmp_path):
    os.chdir(tmp_path)
    
    # 1. git init + configure user identity
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], check=True)
    
    # 2. init + hook-install
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["hook-install"])
    assert result.exit_code == 0
    
    # Ensure hook is present
    pre_commit_path = ".git/hooks/pre-commit"
    assert os.path.exists(pre_commit_path)
    
    # Set up environment with UTF-8 encoding so the Rich panel doesn't crash on legacy codepages (cp1252/cp850)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    
    # 3. git add . + first commit (only .ai/ is modified, check passes)
    subprocess.run(["git", "add", "."], check=True)
    res_commit = subprocess.run(["git", "commit", "-m", "initial commit"], capture_output=True, text=True, encoding="utf-8", env=env)
    
    # If the first commit fails (e.g. because the system can't run sh hooks in this environment), skip the test.
    if res_commit.returncode != 0:
        pytest.skip(f"git cannot execute sh hooks in this environment: {res_commit.stderr}")
        
    # 4. Escribir app.py, git add app.py, commit -> check blocks it
    with open("app.py", "w") as f:
        f.write("print('hello')")
    subprocess.run(["git", "add", "app.py"], check=True)
    
    res_block = subprocess.run(["git", "commit", "-m", "add app.py without updating context"], capture_output=True, text=True, encoding="utf-8", env=env)
    assert res_block.returncode != 0
    
    # 5. Append to .ai/CONTEXT.md, add, commit -> passes
    with open(".ai/CONTEXT.md", "a", encoding="utf-8") as f:
        f.write("\n- added app.py\n")
    subprocess.run(["git", "add", ".ai/CONTEXT.md"], check=True)
    
    res_pass = subprocess.run(["git", "commit", "-m", "add app.py and update context"], capture_output=True, text=True, encoding="utf-8", env=env)
    assert res_pass.returncode == 0


def test_handoff_command(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])

    # Run handoff wizard
    # Inputs:
    # 1. Task type: "feature"
    # 2. What was accomplished: "Implemented feature X"
    # 3. What files changed: "main.py"
    # 4. Add alert: "n"
    # 5. Add decision: "n"
    # 6. Git commit: "n"
    result = runner.invoke(app, ["handoff"], input="feature\nImplemented feature X\nmain.py\nn\nn\nn\n")
    assert result.exit_code == 0
    assert "Recommended model" in result.output

    # Verify CONTEXT.md was updated
    with open(".ai/CONTEXT.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "- Implemented feature X" in content
    assert "- main.py" in content

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    assert today_str in content

def test_triage_shows_model_recommendations(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    assert "Recommended Claude Models" in result.output
    assert "claude-sonnet-4-6" in result.output

def test_handoff_task_type_selection(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])

    # Test with different task types
    task_types = ["architecture", "code_review", "bugfix"]
    for task_type in task_types:
        result = runner.invoke(app, ["handoff"], input=f"{task_type}\nTest\ntest.py\nn\nn\nn\n")
        assert result.exit_code == 0
        assert "Recommended model" in result.output

def test_handoff_shows_reasoning_notice_for_architecture(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["handoff"], input="architecture\nTest\ntest.py\nn\nn\nn\n")
    assert result.exit_code == 0
    assert "extended thinking" in result.output

def test_config_json_models_field_parsed_correctly(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])

    # Verify config.json has models field
    with open(".ai/config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    assert "models" in config
    assert "default" in config["models"]
    assert "recommendations" in config["models"]
    assert "reasoning_tasks" in config["models"]
    assert config["models"]["default"] == "claude-sonnet-4-6"
    assert config["models"]["recommendations"]["architecture"] == "claude-opus-4-8"
    assert "architecture" in config["models"]["reasoning_tasks"]


def test_init_skips_if_ai_folder_exists(tmp_path):
    """init should warn and not overwrite if .ai/ already exists."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0


def test_triage_missing_ai_folder(tmp_path):
    """triage should handle missing .ai/ gracefully without crashing."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["triage"])
    assert result.exit_code in (0, 1)
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_triage_invalid_config_json(tmp_path):
    """triage should handle invalid config.json without crashing."""
    os.chdir(tmp_path)
    os.makedirs(".ai")
    with open(".ai/config.json", "w") as f:
        f.write("not valid json {{{")
    with open(".ai/ALERTS.md", "w", encoding="utf-8") as f:
        f.write("# Alerts\n## P0 — Blocking\n(none)\n## RESOLVED\n")
    result = runner.invoke(app, ["triage"])
    assert result.exit_code in (0, 1)
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_check_no_git_repo(tmp_path):
    """check should exit gracefully when not in a git repo."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0


def test_hook_install_no_git_repo(tmp_path):
    """hook-install should fail gracefully when .git/ does not exist."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["hook-install"])
    assert result.exit_code in (0, 1)
    assert result.exception is None or isinstance(result.exception, SystemExit)


WHEELS_WITH_RULES = """\
# Wheels

## 4. Lint Rules (enforced at pre-commit)

### [LINT-001] No console.log
**Pattern**: `console\\.log\\(`
**Files**: *.js, *.ts
**Message**: Remove console.log before committing.

### [LINT-002] No TODO comments
**Pattern**: `#\\s*TODO`
**Files**: *.py
**Message**: Resolve TODOs before committing.
"""

def test_parse_lint_rules_returns_rules(tmp_path):
    wheels_path = tmp_path / "WHEELS.md"
    wheels_path.write_text(WHEELS_WITH_RULES, encoding="utf-8")
    rules = parse_lint_rules(str(wheels_path))
    assert len(rules) == 2
    assert rules[0]["message"] == "Remove console.log before committing."
    assert "*.js" in rules[0]["files"]
    assert rules[1]["message"] == "Resolve TODOs before committing."


def test_parse_lint_rules_no_section(tmp_path):
    wheels_path = tmp_path / "WHEELS.md"
    wheels_path.write_text("# Wheels\n## 1. Stack\n*(none)*\n", encoding="utf-8")
    rules = parse_lint_rules(str(wheels_path))
    assert rules == []


def test_parse_lint_rules_missing_file(tmp_path):
    rules = parse_lint_rules(str(tmp_path / "nonexistent.md"))
    assert rules == []


def test_check_blocks_on_lint_violation(tmp_path):
    os.chdir(tmp_path)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], check=True)
    runner.invoke(app, ["init"])

    with open(".ai/WHEELS.md", "w", encoding="utf-8") as f:
        f.write(WHEELS_WITH_RULES)

    with open("script.py", "w") as f:
        f.write("x = 1\n# TODO: fix this\ny = 2\n")

    with open("init.txt", "w") as f:
        f.write("init")
    subprocess.run(["git", "add", "init.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "init"], check=True)

    subprocess.run(["git", "add", "script.py", ".ai/WHEELS.md", ".ai/CONTEXT.md"], check=True)
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 1
    assert "WHEELS.md Lint" in result.output


def test_check_passes_with_no_lint_rules(tmp_path):
    os.chdir(tmp_path)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], check=True)
    runner.invoke(app, ["init"])

    with open("init.txt", "w") as f:
        f.write("init")
    subprocess.run(["git", "add", "init.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "init"], check=True)

    with open("script.py", "w") as f:
        f.write("x = 1\n")
    subprocess.run(["git", "add", "script.py", ".ai/CONTEXT.md"], check=True)
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0


def test_update_replaces_section(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["update", "--section", "Current State", "--value", "- new entry"])
    assert result.exit_code == 0
    with open(".ai/CONTEXT.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "- new entry" in content


def test_update_multiline_value(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["update", "--section", "Current State", "--value", "- line1\\n- line2"])
    assert result.exit_code == 0
    with open(".ai/CONTEXT.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "- line1" in content
    assert "- line2" in content


def test_update_missing_section(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["update", "--section", "Nonexistent Section", "--value", "x"])
    assert result.exit_code == 1


def test_update_no_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["update", "--section", "Most recently changed", "--value", "x"])
    assert result.exit_code == 1


def test_snapshot_injects_symbols(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    src = tmp_path / "src" / "mypkg"
    src.mkdir(parents=True)
    (src / "module.py").write_text("def foo(): pass\nclass Bar: pass\n", encoding="utf-8")
    result = runner.invoke(app, ["snapshot", "--src", str(tmp_path / "src")])
    assert result.exit_code == 0
    with open(".ai/CONTEXT.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "Codebase Snapshot" in content
    assert "foo" in content
    assert "Bar" in content


def test_snapshot_no_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["snapshot"])
    assert result.exit_code == 1


def test_action_add_creates_pending(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["action-add", "Create users table", "--type", "db", "--target", "Supabase SQL Editor"])
    assert result.exit_code == 0
    assert "DB-001" in result.output
    with open(".ai/PENDING.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "Create users table" in content
    assert "**Status**: Pending" in content


def test_action_add_with_sql(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["action-add", "Create table", "--type", "db", "--sql", "CREATE TABLE x (id INT);"])
    assert result.exit_code == 0
    with open(".ai/PENDING.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "CREATE TABLE x" in content


def test_action_add_auto_increments(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["action-add", "First", "--type", "db"])
    runner.invoke(app, ["action-add", "Second", "--type", "db"])
    with open(".ai/PENDING.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "DB-001" in content
    assert "DB-002" in content


def test_action_resolve_moves_to_done(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["action-add", "Run migration", "--type", "db"])
    result = runner.invoke(app, ["action-resolve", "DB-001"])
    assert result.exit_code == 0
    with open(".ai/PENDING.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "**Status**: Done" in content
    assert "## DONE" in content


def test_action_resolve_missing_id(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["action-resolve", "DB-999"])
    assert result.exit_code == 1


def test_action_add_no_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["action-add", "Something"])
    assert result.exit_code != 0 or "PENDING" in result.output


def test_handoff_snapshot_flag(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "app.py").write_text("def run(): pass\n", encoding="utf-8")
    result = runner.invoke(
        app, ["handoff", "--snapshot"],
        input="feature\nAdded run fn\napp.py\nn\nn\nn\n"
    )
    assert result.exit_code == 0
    with open(".ai/CONTEXT.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "Codebase Snapshot" in content
    assert "run" in content


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

def test_triage_empty_alerts_file(tmp_path):
    """triage should handle an empty ALERTS.md without crashing."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    with open(".ai/ALERTS.md", "w", encoding="utf-8") as f:
        f.write("")
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    assert result.exception is None


def test_triage_large_alerts_file(tmp_path):
    """triage regex should complete in reasonable time on a large ALERTS.md."""
    import time
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    # Build 500-alert ALERTS.md (~10k lines)
    lines = ["# Active Alerts\n## P0 — Blocking\n"]
    for i in range(1, 501):
        lines.append(
            f"### [ALERT-{i:03d}] Alert number {i}\n"
            f"**Severity**: P0\n**Status**:   Open\n\n"
        )
    lines.append("## RESOLVED\n")
    with open(".ai/ALERTS.md", "w", encoding="utf-8") as f:
        f.writelines(lines)
    start = time.monotonic()
    result = runner.invoke(app, ["triage"])
    elapsed = time.monotonic() - start
    assert result.exit_code == 0
    # 500-alert parse must complete well within 10 seconds
    assert elapsed < 10.0


def test_triage_unicode_alert_titles(tmp_path):
    """triage should handle Unicode characters in alert titles."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    alerts_content = (
        "# Active Alerts\n"
        "## P1 — Important\n"
        "### [ALERT-001] Ünïcödé: 日本語 テスト 🚀\n"
        "**Severity**: P1\n**Status**:   Open\n\n"
        "## RESOLVED\n"
    )
    with open(".ai/ALERTS.md", "w", encoding="utf-8") as f:
        f.write(alerts_content)
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    assert "ALERT-001" in result.output


def test_triage_windows_crlf_alerts(tmp_path):
    """triage should parse ALERTS.md with Windows CRLF line endings."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    alerts_content = (
        "# Active Alerts\r\n"
        "## P0 — Blocking\r\n"
        "### [ALERT-001] CRLF alert\r\n"
        "**Severity**: P0\r\n**Status**:   Open\r\n\r\n"
        "## RESOLVED\r\n"
    )
    with open(".ai/ALERTS.md", "wb") as f:
        f.write(alerts_content.encode("utf-8"))
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    assert "ALERT-001" in result.output


def test_triage_detects_merge_conflict(tmp_path):
    """triage should report merge conflict markers in source files."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    conflict_file = tmp_path / "conflict.py"
    conflict_file.write_text(
        "x = 1\n<<<<<<< HEAD\nfoo = 'ours'\n=======\nfoo = 'theirs'\n>>>>>>> branch\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    assert "conflict" in result.output.lower() or "Merge conflict" in result.output


def test_triage_detects_env_secret(tmp_path):
    """triage should warn about .env files in the working directory."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    with open(".env", "w") as f:
        f.write("SECRET_KEY=hunter2\n")
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    assert ".env" in result.output


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

def test_alert_deduplication_many_duplicates(tmp_path):
    """parse_alerts should return all unique IDs even with many duplicate blocks."""
    from aiorch._helpers import parse_alerts
    alerts_md = tmp_path / "ALERTS.md"
    # Write 50 identical-looking alert blocks
    content = "# Alerts\n## P2 — Noted\n"
    for i in range(1, 51):
        content += f"### [ALERT-{i:03d}] Dup test alert {i}\n**Severity**: P2\n**Status**:   Open\n\n"
    content += "## RESOLVED\n"
    alerts_md.write_text(content, encoding="utf-8")
    alerts = parse_alerts(str(alerts_md))
    ids = [a["id"] for a in alerts]
    assert len(ids) == 50
    assert len(set(ids)) == 50  # all unique


def test_next_action_id_many_existing(tmp_path):
    """_next_action_id should correctly compute the next ID after many entries."""
    from aiorch._helpers import _next_action_id
    pending_md = tmp_path / "PENDING.md"
    lines = ["## Database\n"]
    for i in range(1, 101):
        lines.append(f"### [DB-{i:03d}] Action {i}\n**Status**: Pending\n\n")
    pending_md.write_text("".join(lines), encoding="utf-8")
    next_id = _next_action_id(str(pending_md), "DB")
    assert next_id == "DB-101"


def test_parse_lint_rules_many_rules(tmp_path):
    """parse_lint_rules should handle files with many rule entries."""
    from aiorch._helpers import parse_lint_rules
    lines = ["# Wheels\n\n## 4. Lint Rules (enforced at pre-commit)\n\n"]
    for i in range(1, 21):
        lines.append(
            f"### [LINT-{i:03d}] Rule {i}\n"
            f"**Pattern**: `pattern{i}`\n"
            f"**Files**: *.py\n"
            f"**Message**: Message {i}.\n\n"
        )
    wheels_md = tmp_path / "WHEELS.md"
    wheels_md.write_text("".join(lines), encoding="utf-8")
    rules = parse_lint_rules(str(wheels_md))
    assert len(rules) == 20
    assert rules[-1]["message"] == "Message 20."


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

def test_triage_test_command_failure(tmp_path):
    """triage should report a failed test command without crashing."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    config_path = ".ai/config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    config_data["test_command"] = "exit 1"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    # Should mention test failure
    assert "failed" in result.output.lower() or "error" in result.output.lower()


def test_handoff_invalid_task_type_falls_back(tmp_path):
    """handoff should fall back to 'feature' for unrecognised task types."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["handoff"], input="invalidtype\nDid work\nfile.py\nn\nn\nn\n")
    assert result.exit_code == 0
    assert "Recommended model" in result.output


def test_update_alerts_md_section(tmp_path):
    """update command should work on ALERTS.md, not just CONTEXT.md."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["update", "--section", "P2", "--value", "- custom note", "--file", "ALERTS.md"])
    # Either succeeds or reports section not found — must not crash
    assert result.exit_code in (0, 1)
    assert result.exception is None


def test_action_add_infra_type(tmp_path):
    """action-add should create INFRA-prefix IDs for infra type."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["action-add", "Deploy to prod", "--type", "infra", "--target", "AWS"])
    assert result.exit_code == 0
    assert "INFRA-001" in result.output
    with open(".ai/PENDING.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "Deploy to prod" in content


def test_action_add_other_type(tmp_path):
    """action-add with unknown type should create ACTION-prefix IDs."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["action-add", "Manual step", "--type", "other"])
    assert result.exit_code == 0
    assert "ACTION-001" in result.output


def test_action_resolve_already_done_action(tmp_path):
    """action-resolve on an already-resolved ID should still succeed (idempotent write)."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["action-add", "First action", "--type", "db"])
    runner.invoke(app, ["action-resolve", "DB-001"])
    # Resolving again should either succeed or exit 1, but not crash
    result = runner.invoke(app, ["action-resolve", "DB-001"])
    assert result.exception is None


def test_action_add_unicode_title(tmp_path):
    """action-add should store Unicode titles correctly."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    title = "Créer table 日本語 🗄️"
    result = runner.invoke(app, ["action-add", title, "--type", "db"])
    assert result.exit_code == 0
    with open(".ai/PENDING.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "Créer table" in content


def test_triage_no_pending_file(tmp_path):
    """triage should not crash when PENDING.md does not exist."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    pending = tmp_path / ".ai" / "PENDING.md"
    if pending.exists():
        pending.unlink()
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    assert result.exception is None


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

def test_full_workflow_init_triage_handoff_check(tmp_path):
    """Full workflow: init → triage → handoff → check should all succeed."""
    os.chdir(tmp_path)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], check=True)

    # init
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    # triage
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0

    # handoff — updates CONTEXT.md
    result = runner.invoke(app, ["handoff"], input="feature\nBuilt widget\nwidget.py\nn\nn\nn\n")
    assert result.exit_code == 0

    # Stage a codebase file AND the updated .ai/ file, then check passes
    with open("widget.py", "w") as f:
        f.write("x = 1\n")

    with open("init.txt", "w") as f:
        f.write("init")
    subprocess.run(["git", "add", "init.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "init"], check=True)

    subprocess.run(["git", "add", "widget.py", ".ai/CONTEXT.md"], check=True)
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0


def test_full_workflow_action_add_and_resolve(tmp_path):
    """Full action lifecycle: add multiple actions, resolve them, verify DONE section."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])

    runner.invoke(app, ["action-add", "Create schema", "--type", "db", "--sql", "CREATE TABLE t (id INT);"])
    runner.invoke(app, ["action-add", "Add indexes", "--type", "db"])
    runner.invoke(app, ["action-add", "Deploy infra", "--type", "infra"])

    with open(".ai/PENDING.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "DB-001" in content
    assert "DB-002" in content
    assert "INFRA-001" in content

    runner.invoke(app, ["action-resolve", "DB-001"])
    runner.invoke(app, ["action-resolve", "INFRA-001"])

    with open(".ai/PENDING.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "## DONE" in content
    # DB-002 should still be pending
    pending = [a for a in content.split("### [") if "DB-002" in a]
    assert any("Pending" in block for block in pending)


def test_snapshot_with_syntax_error_file(tmp_path):
    """snapshot should skip files with syntax errors gracefully."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "good.py").write_text("def ok(): pass\n", encoding="utf-8")
    (src / "bad.py").write_text("def broken(:\n", encoding="utf-8")  # syntax error
    result = runner.invoke(app, ["snapshot", "--src", str(tmp_path / "src")])
    assert result.exit_code == 0
    with open(".ai/CONTEXT.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "ok" in content  # good file parsed
    # bad.py should be silently skipped


def test_handoff_with_alert_and_decision(tmp_path):
    """handoff should add alert and decision entries to their respective files."""
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    # Inputs: task=feature, accomplished, files, add_alert=y, id, title, severity, decision=y, id, title, context, commit=n
    result = runner.invoke(
        app, ["handoff"],
        input=(
            "feature\n"
            "Implemented auth\n"
            "auth.py\n"
            "y\n"
            "ALERT-002\n"
            "Auth not rate-limited\n"
            "P1\n"
            "y\n"
            "DEC-001\n"
            "Use JWT tokens\n"
            "Stateless auth required\n"
            "n\n"
        ),
    )
    assert result.exit_code == 0

    with open(".ai/ALERTS.md", "r", encoding="utf-8") as f:
        alerts = f.read()
    assert "ALERT-002" in alerts

    with open(".ai/DECISIONS.md", "r", encoding="utf-8") as f:
        decisions = f.read()
    assert "DEC-001" in decisions
    assert "Use JWT tokens" in decisions


def test_export_stdout(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["export"])
    assert result.exit_code == 0
    assert "## CONTEXT.md" in result.output
    assert "## ALERTS.md" in result.output
    assert "---" in result.output


def test_export_to_file(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    out_path = str(tmp_path / "bundle.md")
    result = runner.invoke(app, ["export", "--out", out_path])
    assert result.exit_code == 0
    assert os.path.exists(out_path)
    with open(out_path, encoding="utf-8") as f:
        content = f.read()
    assert "## CONTEXT.md" in content
    assert "## ALERTS.md" in content


def test_export_no_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["export"])
    assert result.exit_code == 1
    assert "ai-orch init" in result.output


def test_export_missing_files_skipped(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    os.remove(".ai/DISCUSSIONS.md")
    result = runner.invoke(app, ["export"])
    assert result.exit_code == 0
    assert "## DISCUSSIONS.md" not in result.output
    assert "## CONTEXT.md" in result.output


# --- analyze command ---

def test_analyze_no_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code == 1
    assert "ai-orch init" in result.output


def test_analyze_creates_analysis_md(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code == 0
    assert os.path.exists(".ai/ANALYSIS.md")


def test_analyze_status_pending(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["analyze"])
    with open(".ai/ANALYSIS.md", encoding="utf-8") as f:
        content = f.read()
    assert "## Status" in content
    assert "PENDING" in content


def test_analyze_real_metrics_in_report(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["analyze"])
    with open(".ai/ANALYSIS.md", encoding="utf-8") as f:
        content = f.read()
    assert "## Real Metrics" in content
    assert "Open alerts P0" in content
    assert "Pending actions" in content


def test_analyze_self_check_in_output(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code == 0
    assert "Self-Check" in result.output
    assert "Datos reales" in result.output


def test_analyze_uses_agent_role_from_config(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    config_path = ".ai/config.json"
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["agents"] = {"analyzer": {"role": "Eres un agente de prueba especializado."}}
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code == 0
    assert "agente de prueba" in result.output


# --- qa command ---

def test_qa_no_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["qa"])
    assert result.exit_code == 1
    assert "ai-orch init" in result.output


def test_qa_no_analysis_md(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["qa"])
    assert result.exit_code == 1
    assert "ai-orch analyze" in result.output


def test_qa_approves_consistent_analysis(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["analyze"])
    result = runner.invoke(app, ["qa"])
    assert result.exit_code == 0
    assert "APROBADO" in result.output
    with open(".ai/ANALYSIS.md", encoding="utf-8") as f:
        content = f.read()
    assert "QA_APPROVED" in content


def test_qa_already_reviewed_exits_cleanly(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["analyze"])
    runner.invoke(app, ["qa"])
    result = runner.invoke(app, ["qa"])
    assert result.exit_code == 0
    assert "ya revisado" in result.output


def test_qa_escalates_on_discrepancy_human_rejects(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["analyze"])
    # Tamper: change stored P0 count so it mismatches live state
    with open(".ai/ANALYSIS.md", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("| Open alerts P0 | 0 |", "| Open alerts P0 | 5 |")
    with open(".ai/ANALYSIS.md", "w", encoding="utf-8") as f:
        f.write(content)
    # Human says "no" to override
    result = runner.invoke(app, ["qa"], input="n\n")
    assert result.exit_code == 1
    assert "ESCALADO" in result.output
    with open(".ai/ANALYSIS.md", encoding="utf-8") as f:
        final = f.read()
    assert "HUMAN_REVIEWED" in final
    # auto-heal: action should be created in PENDING.md
    with open(".ai/PENDING.md", encoding="utf-8") as f:
        pending = f.read()
    assert "analyze" in pending.lower()


def test_qa_escalates_human_approves_override(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["analyze"])
    with open(".ai/ANALYSIS.md", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("| Open alerts P0 | 0 |", "| Open alerts P0 | 5 |")
    with open(".ai/ANALYSIS.md", "w", encoding="utf-8") as f:
        f.write(content)
    # Human says "yes" to override
    result = runner.invoke(app, ["qa"], input="y\n")
    assert result.exit_code == 0
    assert "Override" in result.output
    with open(".ai/ANALYSIS.md", encoding="utf-8") as f:
        final = f.read()
    assert "QA_APPROVED" in final


# --- observe command ---

def test_observe_not_configured(tmp_path):
    os.chdir(tmp_path)
    with patch("aiorch.main.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_logger.enabled = False
        mock_get_logger.return_value = mock_logger
        result = runner.invoke(app, ["observe"])
    assert result.exit_code == 0
    assert "SUPABASE_URL" in result.output


def test_observe_no_runs_yet(tmp_path):
    os.chdir(tmp_path)
    with patch("aiorch.main.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_logger.enabled = True
        mock_logger.get_recent_runs.return_value = []
        mock_get_logger.return_value = mock_logger
        result = runner.invoke(app, ["observe"])
    assert result.exit_code == 0
    assert "No agent runs" in result.output


def test_observe_shows_table_with_runs(tmp_path):
    os.chdir(tmp_path)
    with patch("aiorch.main.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_logger.enabled = True
        mock_logger.get_recent_runs.return_value = [
            {
                "agent_id": "analyze",
                "command": "analyze",
                "timestamp": "2026-06-07T12:00:00",
                "latency_ms": 500,
                "cost_usd": 0.0,
                "status": "ok",
                "eval_score": None,
            }
        ]
        mock_get_logger.return_value = mock_logger
        result = runner.invoke(app, ["observe"])
    assert result.exit_code == 0
    assert "analyze" in result.output


def test_observe_limit_option(tmp_path):
    os.chdir(tmp_path)
    with patch("aiorch.main.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_logger.enabled = True
        mock_logger.get_recent_runs.return_value = []
        mock_get_logger.return_value = mock_logger
        result = runner.invoke(app, ["observe", "--limit", "5"])
    assert result.exit_code == 0
    mock_logger.get_recent_runs.assert_called_once_with(limit=5)


def test_observe_reports_missing_package(tmp_path):
    os.chdir(tmp_path)
    with patch("aiorch.main.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_logger.enabled = False
        mock_logger.disabled_reason = "package_missing"
        mock_get_logger.return_value = mock_logger
        result = runner.invoke(app, ["observe"])
    assert result.exit_code == 0
    assert "Supabase support is not installed" in result.output
    assert "SUPABASE_URL" not in result.output


def test_qa_override_logs_run(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["analyze"])
    with open(".ai/ANALYSIS.md", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("| Open alerts P0 | 0 |", "| Open alerts P0 | 5 |")
    with open(".ai/ANALYSIS.md", "w", encoding="utf-8") as f:
        f.write(content)
    with patch("aiorch.main.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        result = runner.invoke(app, ["qa"], input="y\n")
    assert result.exit_code == 0
    assert mock_logger.log_run.called
    _, kwargs = mock_logger.log_run.call_args
    assert kwargs.get("status") == "override_approved"



# ---------------------------------------------------------------------------
# sync / brief / ide-install — the non-interactive + cross-IDE surface
# ---------------------------------------------------------------------------

def _git_project(tmp_path):
    """Init a real git repo with .ai/ and one tracked source file."""
    os.chdir(tmp_path)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "config", "user.name", "T"], check=True)
    runner.invoke(app, ["init"])
    os.makedirs("src", exist_ok=True)
    with open("src/auth.py", "w", encoding="utf-8") as f:
        f.write("def login():\n    pass\n")


def test_sync_records_git_changes_without_prompting(tmp_path):
    _git_project(tmp_path)
    # No stdin supplied at all: sync must never block on input.
    result = runner.invoke(app, ["sync", "--note", "Stopped at JWT refresh"])
    assert result.exit_code == 0, result.output
    assert "[OK]" in result.output
    content = open(".ai/CONTEXT.md", encoding="utf-8").read()
    assert "Stopped at JWT refresh" in content
    assert "src/auth.py" in content          # derived from git, never typed
    assert "## Codebase Snapshot" in content # snapshot refreshed


def test_sync_warns_when_note_omitted(tmp_path):
    _git_project(tmp_path)
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    assert "[WARN]" in result.output
    assert "only you know WHY" in result.output


def test_sync_excludes_ai_folder_from_changed_files(tmp_path):
    _git_project(tmp_path)
    runner.invoke(app, ["sync", "--note", "n"])
    changed = open(".ai/CONTEXT.md", encoding="utf-8").read()
    changed = changed.split("**Most recently changed:**")[1].split("---")[0]
    assert ".ai/" not in changed


def test_sync_falls_back_to_last_commit_when_tree_clean(tmp_path):
    _git_project(tmp_path)
    subprocess.run(["git", "add", "src/auth.py"], check=True)
    subprocess.run(["git", "commit", "-m", "feat: auth"], check=True, capture_output=True)
    result = runner.invoke(app, ["sync", "--note", "after commit"])
    assert result.exit_code == 0
    assert "src/auth.py" in open(".ai/CONTEXT.md", encoding="utf-8").read()


def test_sync_requires_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_brief_renders_live_state(tmp_path):
    _git_project(tmp_path)
    runner.invoke(app, ["action-add", "Add index", "--type", "db"])
    result = runner.invoke(app, ["brief"])
    assert result.exit_code == 0
    assert "project status" in result.output
    assert "What needs a person" in result.output
    assert "DB-001" in result.output


def test_brief_writes_to_out_file(tmp_path):
    _git_project(tmp_path)
    result = runner.invoke(app, ["brief", "--out", "STATUS.md"])
    assert result.exit_code == 0
    assert "[OK]" in result.output
    assert "project status" in open("STATUS.md", encoding="utf-8").read()


def test_brief_flags_p0_in_headline(tmp_path):
    _git_project(tmp_path)
    from aiorch.alerts import insert_alert
    insert_alert(".ai/ALERTS.md", {"id": "ALERT-001", "title": "Boom", "severity": "P0"}, "2026-08-31")
    result = runner.invoke(app, ["brief"])
    assert "blocking issue" in result.output
    assert "ALERT-001" in result.output


def test_ide_install_creates_agents_md_and_antigravity_rule(tmp_path):
    _git_project(tmp_path)
    result = runner.invoke(app, ["ide-install"])
    assert result.exit_code == 0
    agents = open("AGENTS.md", encoding="utf-8").read()
    assert "ai-orch:start" in agents and "ai-orch:end" in agents
    assert ".ai/CONTEXT.md" in agents
    rule = open(os.path.join(".agents", "rules", "ai-orch.md"), encoding="utf-8").read()
    assert rule.startswith("---\ntrigger: always_on")


def test_ide_install_preserves_hand_written_agents_md(tmp_path):
    _git_project(tmp_path)
    with open("AGENTS.md", "w", encoding="utf-8") as f:
        f.write("# Agent instructions\n\n## House rules\n- Never touch billing/.\n")
    runner.invoke(app, ["ide-install"])
    # Regenerating must not eat the user's own text, before or after our block.
    runner.invoke(app, ["ide-install"])
    agents = open("AGENTS.md", encoding="utf-8").read()
    assert "Never touch billing/." in agents
    assert agents.count("ai-orch:start") == 1


def test_ide_install_no_antigravity_flag(tmp_path):
    _git_project(tmp_path)
    result = runner.invoke(app, ["ide-install", "--no-antigravity"])
    assert result.exit_code == 0
    assert os.path.exists("AGENTS.md")
    assert not os.path.exists(os.path.join(".agents", "rules", "ai-orch.md"))


def test_ide_install_requires_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["ide-install"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# validate / roles / the CLAUDE.md discovery gap
# ---------------------------------------------------------------------------

_VALID_PLAN = (
    '{"schema":"ai-orch/v1","role":"planner","task_id":"T-1","status":"ok",'
    '"summary":"plan","evidence":["read src/"],"next_role":"executor",'
    '"steps":[{"id":"S-1","goal":"g","done_when":"tests pass"}]}'
)


def test_validate_accepts_a_good_envelope_and_prints_routing(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["validate", _VALID_PLAN])
    assert result.exit_code == 0, result.output
    assert "[OK]" in result.output
    assert "executor" in result.output


def test_validate_reads_from_a_file(tmp_path):
    os.chdir(tmp_path)
    with open("env.json", "w", encoding="utf-8") as f:
        f.write(_VALID_PLAN)
    result = runner.invoke(app, ["validate", "env.json"])
    assert result.exit_code == 0


def test_validate_rejects_and_lists_every_violation(tmp_path):
    os.chdir(tmp_path)
    bad = '{"schema":"ai-orch/v1","role":"planner","task_id":"T-1","status":"ok","next_role":"qa"}'
    result = runner.invoke(app, ["validate", bad])
    assert result.exit_code == 1
    assert "[ERROR]" in result.output
    # summary missing, steps missing, evidence missing, illegal transition
    assert "violation" in result.output
    assert "next_role" in result.output


def test_validate_role_mismatch_fails(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["validate", _VALID_PLAN, "--role", "executor"])
    assert result.exit_code == 1
    assert "expected role" in result.output


def test_validate_bad_json_is_an_error_not_a_crash(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["validate", "{not json"])
    assert result.exit_code == 1
    assert "[ERROR]" in result.output


def test_roles_lists_versioned_prompts(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["roles"])
    assert result.exit_code == 0
    for role in ("planner", "executor", "qa_reviewer", "analyzer"):
        assert role in result.output


def test_roles_warns_on_unversioned_prompt(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    with open(".ai/config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["agents"]["planner"].pop("version")
    with open(".ai/config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    result = runner.invoke(app, ["roles"])
    assert "[WARN]" in result.output
    assert "unversioned" in result.output


def test_roles_requires_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["roles"])
    assert result.exit_code == 1


def test_ide_install_closes_the_claude_md_discovery_gap(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["ide-install"])
    assert result.exit_code == 0
    claude_md = open("CLAUDE.md", encoding="utf-8").read()
    # @-prefixed paths are imports, not references — that is the whole point.
    assert "@.ai/ORCHESTRATOR.md" in claude_md
    assert "@.ai/ALERTS.md" in claude_md
    assert "ai-orch:start" in claude_md


def test_ide_install_preserves_hand_written_claude_md(tmp_path):
    os.chdir(tmp_path)
    runner.invoke(app, ["init"])
    with open("CLAUDE.md", "w", encoding="utf-8") as f:
        f.write("# CLAUDE.md\n\n## House rules\n- Never touch billing/.\n")
    runner.invoke(app, ["ide-install"])
    runner.invoke(app, ["ide-install"])
    claude_md = open("CLAUDE.md", encoding="utf-8").read()
    assert "Never touch billing/." in claude_md
    assert claude_md.count("ai-orch:start") == 1
