import typer
from pathlib import Path
from turbines import builder, server

app = typer.Typer()


@app.command()
def create(path: Path):
    """Scaffold a new project structure (pages, templates, static)."""
    builder.initialize_directory(path)
    print(f"Created project at {path}")


@app.command()
def build(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force overwrite of existing files in output directory before serving",
    ),
):
    """Render pages to the build folder."""

    try:
        _builder = builder.Builder(force_files_overwrite=force)
    except ValueError as e:
        print(f"Error: {e}")
        print("Aborting build to avoid overwriting files.")
        raise typer.Exit(code=1)
    _builder.load()
    _builder.render_pages()


@app.command()
def serve(
    watch: bool = typer.Option(True, help="Enable hot-reloading"),
    host: str = typer.Option("127.0.0.1", help="Host to bind the server"),
    port: int = typer.Option(8000, help="Port to bind the server"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force overwrite of existing files in output directory before serving",
    ),
):
    """Run local server with hot-reloading."""

    try:
        server.run_server(
            watch=watch, host=host, port=port, force_files_overwrite=force
        )
    except ValueError as e:
        print(f"Error: {e}")
        print("Aborting server start to avoid overwriting files.")
        raise typer.Exit(code=1)


def main() -> None:
    app()
