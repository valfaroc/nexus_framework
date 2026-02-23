import typer

app = typer.Typer(name="nexus", help="Modular, simulator-agnostic CCAM simulation framework")


@app.command()
def up() -> None:
    """Launch all simulation services defined in nexus.yaml."""
    typer.echo("nexus up — not yet implemented")


@app.command()
def down() -> None:
    """Stop all running Nexus services."""
    typer.echo("nexus down — not yet implemented")


@app.command()
def new(project_name: str) -> None:
    """Scaffold a new Nexus project."""
    typer.echo(f"nexus new {project_name} — not yet implemented")


if __name__ == "__main__":
    app()
