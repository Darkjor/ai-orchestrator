import os
import shutil
import json
import re
import subprocess
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help="Global AI Orchestrator CLI")
console = Console()

def parse_alerts(alerts_path: str):
    """Parse alerts file and return open P0, P1, P2 alerts."""
    if not os.path.exists(alerts_path):
        return []
    
    alerts = []
    current_severity = "P2" # Default fallback
    
    with open(alerts_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for line in lines:
        stripped = line.strip()
        # Detect section severity
        if stripped.startswith("## P0"):
            current_severity = "P0"
        elif stripped.startswith("## P1"):
            current_severity = "P1"
        elif stripped.startswith("## P2"):
            current_severity = "P2"
        elif stripped.startswith("## RESOLVED"):
            current_severity = "RESOLVED"
        
        # Detect alert item
        if stripped.startswith("### [ALERT-"):
            # Extract ID and title
            match = re.search(r"### \[(ALERT-\d+)\]\s*(.*)", stripped)
            if match:
                alert_id = match.group(1)
                title = match.group(2)
                if current_severity != "RESOLVED":
                    alerts.append({
                        "id": alert_id,
                        "title": title,
                        "severity": current_severity,
                        "status": "Open"
                    })
    return alerts

@app.command()
def init():
    """Initialize .ai/ orchestrator folder in current directory."""
    if os.path.exists(".ai"):
        console.print("[yellow]Warning: .ai directory already exists.[/yellow]")
        raise typer.Exit()
    
    os.makedirs(".ai", exist_ok=True)
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    
    if not os.path.exists(template_dir):
        console.print(f"[red]Error: Templates directory {template_dir} not found.[/red]")
        raise typer.Exit(1)
        
    for filename in os.listdir(template_dir):
        src = os.path.join(template_dir, filename)
        dst = os.path.join(".ai", filename)
        shutil.copy(src, dst)
    
    console.print("[green]Successfully initialized .ai/ orchestrator folder![/green]")

@app.command()
def triage():
    """Triage active project alerts and check codebase health."""
    if not os.path.exists(".ai"):
        console.print("[red]Error: .ai/ orchestrator folder not found. Run 'ai-orch init' first.[/red]")
        raise typer.Exit(1)
        
    # 1. Parse active alerts
    alerts_path = os.path.join(".ai", "ALERTS.md")
    alerts = parse_alerts(alerts_path)
    
    console.print(Panel("[bold blue]AI Orchestrator — Project Triage[/bold blue]", expand=False))
    
    # Render Alerts Table
    if alerts:
        table = Table(title="Active Alerts", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=12)
        table.add_column("Severity", style="bold")
        table.add_column("Title")
        table.add_column("Status", justify="right")
        
        for alert in alerts:
            sev_color = "red" if alert["severity"] == "P0" else ("yellow" if alert["severity"] == "P1" else "blue")
            table.add_column = table.add_row(
                alert["id"],
                f"[{sev_color}]{alert['severity']}[/{sev_color}]",
                alert["title"],
                "[green]Open[/green]"
            )
        console.print(table)
    else:
        console.print("[green]✔ No active alerts found in ALERTS.md[/green]")
        
    # 2. Check for Git merge conflicts
    console.print("\n[bold]Checking for git merge conflicts...[/bold]")
    conflict_found = False
    for root, dirs, files in os.walk("."):
        # Skip common directories
        if any(ignored in root for ignored in [".git", "venv", ".venv", "node_modules", "__pycache__", ".pytest_cache"]):
            continue
        for file in files:
            file_path = os.path.join(root, file)
            # Only read text files
            if not file.endswith((".py", ".gd", ".go", ".js", ".ts", ".json", ".md", ".txt", ".html", ".xml", ".yml", ".yaml")):
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if "<<<<<<<" in content and "=======" in content:
                        console.print(f"[red]✗ Merge conflict found in {file_path}[/red]")
                        conflict_found = True
            except Exception:
                pass
    if not conflict_found:
        console.print("[green]✔ No active merge conflicts detected.[/green]")
        
    # 3. Check for exposed secrets/credentials
    console.print("\n[bold]Checking for exposed secrets...[/bold]")
    staged_secrets = []
    # If it is a git repo, check staged files
    if os.path.exists(".git"):
        try:
            res = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True)
            staged_files = res.stdout.splitlines()
            for f in staged_files:
                if f.endswith(".env") or "secret" in f.lower() or f.endswith(".pem") or f.endswith(".key"):
                    staged_secrets.append(f)
        except Exception:
            pass
            
    # Check current directory for unstaged plain secrets
    for f in os.listdir("."):
        if f.endswith(".env") or f.endswith(".pem") or f.endswith(".key"):
            staged_secrets.append(f)
            
    if staged_secrets:
        for sec in set(staged_secrets):
            console.print(f"[yellow]⚠ Warning: Potential secret file detected: {sec}[/yellow]")
    else:
        console.print("[green]✔ No secret/credential leaks detected.[/green]")

    # 4. Run test command if configured
    config_path = os.path.join(".ai", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            test_cmd = config.get("test_command")
            if test_cmd:
                console.print(f"\n[bold]Running test command: {test_cmd}...[/bold]")
                # Run the command in the shell
                test_res = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
                if test_res.returncode == 0:
                    console.print("[green]✔ Tests passed successfully![/green]")
                else:
                    console.print(f"[red]✗ Test command failed with exit code {test_res.returncode}[/red]")
                    if test_res.stdout:
                        console.print(test_res.stdout)
                    if test_res.stderr:
                        console.print(test_res.stderr)
        except Exception as e:
            console.print(f"[yellow]⚠ Warning: Could not run test command. Reason: {e}[/yellow]")

if __name__ == "__main__":
    app()
