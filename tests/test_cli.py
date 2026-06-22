import os
import json
import subprocess
import datetime
from typer.testing import CliRunner
from aiorch.main import app

runner = CliRunner()

def test_init_creates_ai_folder(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert os.path.exists(".ai")
    assert os.path.exists("AGENTS.md")
    assert not os.path.exists(".ai/AGENTS.md")


def test_init_does_not_overwrite_existing_agents_md(tmp_path):
    os.chdir(tmp_path)
    with open("AGENTS.md", "w", encoding="utf-8") as f:
        f.write("custom existing agents file")
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    with open("AGENTS.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert content == "custom existing agents file"

def test_init_detects_python_project(tmp_path):
    os.chdir(tmp_path)
    with open("pyproject.toml", "w", encoding="utf-8") as f:
        f.write('[project]\nname = "my-detected-app"\n\n[project.scripts]\nmy-cli = "my_detected_app.main:app"\n')
    os.makedirs("tests", exist_ok=True)

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    with open(".ai/config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    assert config["project_name"] == "my-detected-app"
    assert config["project_stack"] == "Python"
    assert config["project_type"] == "CLI"
    assert config["run_command"] == "my-cli --help"
    assert config["test_command"] == "pytest"


def test_init_detects_node_project(tmp_path):
    os.chdir(tmp_path)
    with open("package.json", "w", encoding="utf-8") as f:
        json.dump({"name": "my-node-app", "scripts": {"start": "node index.js", "test": "jest"}}, f)

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    with open(".ai/config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    assert config["project_name"] == "my-node-app"
    assert config["project_stack"] == "Node.js"
    assert config["run_command"] == "npm start"
    assert config["test_command"] == "npm test"


def test_init_falls_back_to_directory_name(tmp_path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    with open(".ai/config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    assert config["project_name"] == tmp_path.name
    assert config["project_stack"] == "Unknown"


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

def test_check_accepts_agents_md_update(tmp_path):
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

    with open("AGENTS.md", "a") as f:
        f.write("\nUpdated agent instructions")
    subprocess.run(["git", "add", "AGENTS.md"], check=True)

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
