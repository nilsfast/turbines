import asyncio
import os
import logging
import tornado.web
import tornado.websocket
import tornado.httpserver
from watchfiles import awatch

from turbines.builder import Builder
from turbines.server_handlers import LiveReloadWebSocketHandler, CustomStaticFileHandler

log = logging.getLogger(__name__)


def _make_reload_script(host: str, port: int) -> str:
    return f"""
<script>
    function connectWebSocket() {{
        let ws = new WebSocket("ws://{host}:{port}/_turbines/livereload");
        ws.onmessage = (event) => {{
            if (event.data === "reload") {{
                console.log("Reload message received, reloading page...");
                window.location.reload();
            }}
        }};
        ws.onopen = () => {{
            console.log("LiveReload WebSocket connection established.");
        }};
        ws.onclose = () => {{
            console.log("LiveReload WebSocket connection closed, reconnecting in 5s...");
            setTimeout(connectWebSocket, 5000);
        }};
    }}
    connectWebSocket();
</script>
"""


def _notify_clients(clients: list) -> None:
    """Send a reload message to all connected WebSocket clients (must run on the IO loop)."""
    for client in list(clients):
        try:
            client.write_message("reload")
        except Exception as e:
            log.error(f"Error notifying client: {e}")
            clients.remove(client)


class TurbinesServer:
    def __init__(self, watch: bool = False, force_files_overwrite: bool = False):
        self._watch = watch
        self._clients: list[tornado.websocket.WebSocketHandler] = []
        self._reload_script: str | None = None

        self.builder = Builder(
            base_dir=os.getcwd(), force_files_overwrite=force_files_overwrite
        )
        self.builder.load()
        self.builder.render_pages()

    async def _watch_loop(self) -> None:
        """Async coroutine that watches source files via watchfiles."""
        source_dir = os.path.abspath(self.builder.base_dir)
        build_dir = os.path.abspath(self.builder.build_path)

        log.info(f"Watching for changes in {source_dir}")

        # Suppress watchfiles logging to reduce noise during development
        logging.getLogger("watchfiles").setLevel(logging.WARNING)

        async for changes in awatch(
            source_dir,
            raise_interrupt=False,
        ):
            # Ignore events that originate inside the build output directory
            relevant = [
                path
                for _, path in changes
                if not os.path.abspath(path).startswith(build_dir)
            ]
            if not relevant:
                continue

            print()
            log.info(
                f"Changes detected ({len(relevant)} file(s)), rebuilding...",
            )

            log.debug(f"Changed files: {relevant}")

            # If the config is changed, we need to reload it before rendering pages
            if any(
                os.path.abspath(path) == os.path.abspath(self.builder.config_path)
                for path in relevant
            ):
                log.warning("Config changed!")

                self.builder.load_config()
                self.builder._post_load_config()  # re-apply config settings to builder (e.g. build_path, etc.)

            try:
                self.builder.load()
                self.builder.render_pages()

            # TODO catch more specific exceptions from the builder and log them accordingly (e.g. syntax errors in templates, etc.)
            except Exception as e:
                log.error(f"Build error: {e}")
                continue

            # Notify browser clients
            _notify_clients(self._clients)

    def _build_tornado_app(self, host: str, port: int) -> tornado.web.Application:
        self._reload_script = _make_reload_script(host, port)

        return tornado.web.Application(
            [
                (
                    r"/_turbines/livereload",
                    LiveReloadWebSocketHandler,
                    {"clients": self._clients},
                ),
                (
                    r"/(.*)",
                    CustomStaticFileHandler,
                    {
                        "path": self.builder.build_path,
                        "default_filename": "index.html",
                        "extensionless_urls": self.builder.config.site.extensionless_urls,
                        "inject_reload_script": self._watch,
                        "reload_script": self._reload_script,
                    },
                ),
            ]
        )

    async def serve(self, host: str, port: int) -> None:
        if self._watch:
            log.info("Starting in watch mode with hot-reloading enabled.")
            asyncio.create_task(self._watch_loop())

        # supress tornado access logs to reduce noise during development
        logging.getLogger("tornado").setLevel(logging.WARNING)

        # Build and run the Tornado app to serve build output
        app = self._build_tornado_app(host, port)
        server = tornado.httpserver.HTTPServer(app)
        server.listen(port, address=host)
        log.info(f"Serving {self.builder.build_path} at http://{host}:{port}")

        await asyncio.Event().wait()  # run until interrupted

    def run(self, host: str = "localhost", port: int = 8000) -> None:
        asyncio.run(self.serve(host, port))
