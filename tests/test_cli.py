import os
import json
import subprocess
from typer.testing import CliRunner
from aiorch.main import app

runner = CliRunner()

def test_placeholder():
    assert True

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
    # Init git and ai folder
    subprocess.run(["git", "init"], check=True, capture_output=True)
    runner.invoke(app, ["init"])
    
    # Configure git username for commits in tests
    subprocess.run(["git", "config", "user.name", "Test User"], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
    
    # Initial commit so we have a HEAD
    with open("init_file.txt", "w") as f:
        f.write("initial file")
    subprocess.run(["git", "add", "init_file.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], check=True)
    
    # Modify a source file and stage it
    with open("source.py", "w") as f:
        f.write("print('hello')")
    subprocess.run(["git", "add", "source.py"], check=True)
    
    # Run check. Since no .ai files are modified, it should fail (exit_code != 0)
    result = runner.invoke(app, ["check"])
    assert result.exit_code != 0
    assert "Error" in result.output or "warning" in result.output.lower() or "missing" in result.output.lower()
    
    # Now stage .ai/CONTEXT.md modification
    with open(".ai/CONTEXT.md", "a") as f:
        f.write("\nUpdated context for test")
    subprocess.run(["git", "add", ".ai/CONTEXT.md"], check=True)
    
    # Run check again. It should succeed (exit_code == 0)
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
