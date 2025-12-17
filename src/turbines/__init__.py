import typer
from pathlib import Path
from turbines import builder, server

app = typer.Typer()


@app.command()
def create(path: Path):
    """Scaffold a new project structure (pages, templates, static)."""
    builder.scaffold(path)
    print(f"Created project at {path}")


@app.command()
def build():
    """Render pages to the build folder."""

    _builder = builder.Builder()
    _builder.load()
    _builder.build_site()


@app.command()
def serve(
    watch: bool = typer.Option(True, help="Enable hot-reloading"),
    host: str = typer.Option("127.0.0.1", help="Host to bind the server"),
    port: int = typer.Option(8000, help="Port to bind the server"),
):
    """Run local server with hot-reloading."""

    server.run_server(watch=watch, host=host, port=port)


def main() -> None:
    app()
