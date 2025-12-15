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
def serve():
    """Run local server with hot-reloading."""

    server.run_server(watch=True)


def main() -> None:
    app()
