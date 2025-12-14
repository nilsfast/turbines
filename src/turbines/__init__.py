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
    builder.build_site()


@app.command()
def serve():
    """Run local server with hot-reloading."""
    server.start_watching()
    server.run_server()


def main() -> None:
    app()
