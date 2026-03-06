import logging

import typer
from pathlib import Path
from turbines import builder
from turbines.server import TurbinesServer
from turbines.logging_setup import setup_logging
from importlib.metadata import version as get_version

__version__ = get_version(__package__ or "turbines")

app = typer.Typer()


def setup():
    print(f"Turbines Version {__version__}")
    setup_logging("INFO")


def version_callback(value: bool):
    if value:
        print(f"Turbines Version: {__version__}")
        raise typer.Exit()


@app.command()
def create(path: Path):
    """Scaffold a new project structure (pages, templates, static)."""
    setup()
    log = logging.getLogger(__name__)

    builder.initialize_project(path)
    log.info(f"Created project at {path}")


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
    setup()
    log = logging.getLogger(__name__)

    try:
        _builder = builder.Builder(force_files_overwrite=force)
    except RuntimeError as e:
        log.error(f"Error building site: {e}")
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
    setup()
    log = logging.getLogger(__name__)

    try:
        server = TurbinesServer(watch=watch, force_files_overwrite=force)
        server.run(host, port)
    except RuntimeError as e:
        log.error(f"Error starting server: {e}")
        raise typer.Exit(code=1)
    finally:
        raise typer.Exit(code=1)
