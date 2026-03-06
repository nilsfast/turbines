import os
import tornado.websocket


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
