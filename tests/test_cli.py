import os
import json
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
    # Run init to get folders
    runner.invoke(app, ["init"])
    
    # Overwrite ALERTS.md with a mock open P0 alert
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
        
    # Configure test command to run a simple echo in config.json
    config_path = ".ai/config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    config_data["test_command"] = "echo 'Tests run successfully'"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
        
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    # Should list ALERT-001 in stdout
    # Note: we check the bytes/stdout to verify ALERT-001 is mentioned
    assert "ALERT-001" in result.output
