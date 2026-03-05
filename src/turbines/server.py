import os
import threading

from watchfiles import watch
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.httpserver

from turbines.builder import Builder
import logging

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
            print(f"Error notifying client: {e}")
            clients.remove(client)


class LiveReloadWebSocketHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, clients: list) -> None:
        self._clients = clients

    def open(self, *args, **kwargs) -> None:
        self._clients.append(self)

    def on_close(self) -> None:
        self._clients.remove(self)

    def on_message(self, message: str | bytes) -> None:
        pass  # clients never send messages

    def check_origin(self, origin: str) -> bool:
        return True  # allow all origins during development


class CustomStaticFileHandler(tornado.web.StaticFileHandler):
    """
    Static file handler with optional live-reload script injection and
    extensionless URL support.

    Extra ``initialize`` kwargs:
        - ``inject_reload_script`` (bool): inject livereload ``<script>`` into HTML.
        - ``extensionless_urls`` (bool): resolve extensionless paths to ``.html`` files.
        - ``reload_script`` (str | None): the script tag to inject.
    """

    def initialize(
        self,
        path: str,
        default_filename: str | None = None,
        inject_reload_script: bool = False,
        extensionless_urls: bool = False,
        reload_script: str | None = None,
    ) -> None:
        super().initialize(path=path, default_filename=default_filename)
        self.inject_reload_script = inject_reload_script
        self.extensionless_urls = extensionless_urls
        self.reload_script = reload_script

    def _inject_script(self, content: str) -> str:
        assert self.reload_script is not None, "reload_script is not set"
        if "</body>" in content:
            return content.replace("</body>", self.reload_script + "</body>")
        return content + self.reload_script

    async def get(self, path: str, include_body: bool = True) -> None:
        orig_path = path

        # Resolve directory / extensionless paths to index.html / <name>.html
        if path == "" or path.endswith("/"):
            path = os.path.join(path, "index.html")
        elif self.extensionless_urls and not os.path.splitext(path)[1]:
            html_path = os.path.join(self.root, path + ".html")
            index_path = os.path.join(self.root, path, "index.html")
            if os.path.exists(html_path):
                path = path + ".html"
            elif os.path.exists(index_path):
                path = os.path.join(path, "index.html")

        # Non-HTML files: delegate to the standard handler
        if not path.endswith(".html"):
            await super().get(orig_path, include_body)
            return

        abs_path = self.get_absolute_path(self.root, path)
        if not os.path.exists(abs_path):
            raise tornado.web.HTTPError(404)

        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.set_header("Content-Type", "text/html; charset=UTF-8")
        if self.inject_reload_script:
            content = self._inject_script(content)
        self.write(content)
        await self.flush()


class TurbinesServer:
    def __init__(self, watch: bool = False, force_files_overwrite: bool = False):
        self._watch = watch
        self._clients: list[tornado.websocket.WebSocketHandler] = []
        self._reload_script: str | None = None
        self._stop_event = threading.Event()

        self.builder = Builder(
            base_dir=os.getcwd(), force_files_overwrite=force_files_overwrite
        )
        self.builder.load()
        self.builder.render_pages()

    def _start_watcher(self, loop: tornado.ioloop.IOLoop) -> None:
        """Launch a daemon thread that watches source files via watchfiles."""
        source_dir = os.path.abspath(self.builder.base_dir)
        build_dir = os.path.abspath(self.builder.build_path)

        log.info(f"Watching for changes in {source_dir}")

        def _watch_loop() -> None:
            for changes in watch(
                source_dir,
                stop_event=self._stop_event,
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
                try:
                    self.builder.load()
                    self.builder.render_pages()
                except Exception as e:
                    print(f"Build error: {e}")
                    return

                # Notify browser clients on the IO thread
                loop.add_callback(_notify_clients, self._clients)

        thread = threading.Thread(
            target=_watch_loop, daemon=True, name="turbines-watcher"
        )
        thread.start()

    def _build_app(self, host: str, port: int) -> tornado.web.Application:
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

    def serve(self, host: str, port: int) -> None:
        os.chdir(self.builder.build_path)
        app = self._build_app(host, port)
        server = tornado.httpserver.HTTPServer(app)
        server.listen(port, address=host)
        log.info(f"Serving {self.builder.build_path} at http://{host}:{port}")

    def run(self, host: str = "localhost", port: int = 8000) -> None:
        loop = tornado.ioloop.IOLoop.current()

        if self._watch:
            self._start_watcher(loop)

        try:
            self.serve(host, port)
            loop.start()
        except KeyboardInterrupt:
            log.info("Shutting down server...")
            self._stop_event.set()
            loop.stop()
