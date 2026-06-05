import os
import shutil
import json
import typer
from rich.console import Console

app = typer.Typer(help="Global AI Orchestrator CLI")
console = Console()

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
    """Placeholder triage command."""
    pass

if __name__ == "__main__":
    app()
