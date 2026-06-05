import typer

app = typer.Typer(help="Global AI Orchestrator CLI")

@app.command()
def hello():
    print("Hello from ai-orchestrator!")

if __name__ == "__main__":
    app()
