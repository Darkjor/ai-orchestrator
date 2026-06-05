import os
from typer.testing import CliRunner
from aiorch.main import app

runner = CliRunner()

def test_placeholder():
    assert True

def test_init_creates_ai_folder(tmp_path):
    # Change current working directory to a temporary path
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert os.path.exists(".ai")
    assert os.path.exists(".ai/ORCHESTRATOR.md")
    assert os.path.exists(".ai/CONTEXT.md")
    assert os.path.exists(".ai/ALERTS.md")
    assert os.path.exists(".ai/DECISIONS.md")
    assert os.path.exists(".ai/WHEELS.md")
    assert os.path.exists(".ai/DISCUSSIONS.md")
    assert os.path.exists(".ai/config.json")
