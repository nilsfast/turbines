import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from turbines.builder import Builder

import threading
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.httpserver


CLIENTS = []
LIVE_RELOAD_SCRIPT = None


def make_reload_script(host: str, port: int) -> str:
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
            console.log("LiveReload WebSocket connection closed, reconnecting in 1s...");
            setTimeout(connectWebSocket, 5000);
        }};
    }}
    connectWebSocket();
</script>
"""


def notify_client_refresh():
    # print("Notifying clients to reload...")
    for client in list(CLIENTS):
        try:
            client.write_message("reload")
        except:
            CLIENTS.remove(client)


class ChangeHandler(FileSystemEventHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dist_path = os.path.abspath("dist")
        self._debounce_timer = None
        self._debounce_delay = 0.3  # seconds

    def set_loop(self, loop):
        self.__loop = loop

    def set_builder_ref(self, builder: Builder):
        self._builder = builder

    def _handle_change(self, path):

        # Ignore changes in the dist directory
        if path.startswith(self._dist_path):
            return

        print(f"File change detected in {path}, scheduling reload notification...")

        load_static = True if "static" in path else False

        if self.__loop:
            self._builder.reload(
                load_static=load_static,
            )
            self.__loop.add_callback(notify_client_refresh)

    def on_modified(self, event):
        path = os.path.abspath(event.src_path)
        if event.is_directory:
            return
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(
            self._debounce_delay, self._handle_change, args=(path,)
        )
        self._debounce_timer.start()


class LiveReloadWebSocketHandler(tornado.websocket.WebSocketHandler):

    def open(self, *args, **kwargs):
        # print("LiveReload client connected.")
        CLIENTS.append(self)

    def on_close(self):
        CLIENTS.remove(self)

    def on_message(self, message: str | bytes):

        pass

    def check_origin(self, origin: str) -> bool:
        return True  # Allow connections from any origin


class StaticFileHandler(tornado.web.StaticFileHandler):
    async def get(self, path, include_body=True):
        # Serve /index.html for root or empty path
        if path == "" or path == "/":
            path = "index.html"
        await super().get(path, include_body)


class StaticFileHandlerWithReload(tornado.web.StaticFileHandler):
    async def get(self, path, include_body=True):
        # Serve /index.html for root or empty path
        if path == "" or path == "/":
            path = "index.html"
        absolute_path = self.get_absolute_path(self.root, path)
        if path.endswith(".html") and os.path.exists(absolute_path):
            # print("Injecting LiveReload script into", path)
            with open(absolute_path, "r", encoding="utf-8") as f:
                html = f.read()
            # Inject the reload script before </body> if present, else at the end
            assert LIVE_RELOAD_SCRIPT is not None, "LIVE_RELOAD_SCRIPT is not set!"
            if "</body>" in html:
                html = html.replace("</body>", LIVE_RELOAD_SCRIPT + "</body>")
            else:
                html += LIVE_RELOAD_SCRIPT
            self.set_header("Content-Type", "text/html; charset=UTF-8")
            self.write(html)
            await self.flush()
        else:
            await super().get(path, include_body)


class TurbineServer:
    def __init__(self, watch: bool = False):
        self.watch = watch
        self.builder = Builder(inject_reload_script=True)
        self.builder.load()
        self.builder.build_site()

    def serve(self, host: str, port: int):
        os.chdir(self.builder.build_path)
        print(f"Serving '{self.builder.build_path}' at http://{host}:{port} ...")
        print("Do not use in production!")

        # set up live reload script
        global LIVE_RELOAD_SCRIPT
        LIVE_RELOAD_SCRIPT = make_reload_script(host, port)

        handler = StaticFileHandlerWithReload
        if not self.watch:
            handler = StaticFileHandler

        self.app = tornado.web.Application(
            [
                (r"/_turbines/livereload", LiveReloadWebSocketHandler),
                (
                    r"/(.*)",
                    handler,
                    {"path": self.builder.build_path},
                ),
            ]
        )
        server = tornado.httpserver.HTTPServer(self.app)
        server.listen(port, address=host)

    def run(self, host: str = "localhost", port: int = 8000):
        loop = tornado.ioloop.IOLoop.current()
        observer = None
        if self.watch:
            observer = Observer()
            handler = ChangeHandler()
            handler.set_loop(loop)
            handler.set_builder_ref(self.builder)
            observer.schedule(handler, path=os.path.join(os.getcwd()), recursive=True)
            observer.start()
        try:
            self.serve(host, port)
            tornado.ioloop.IOLoop.current().start()
        finally:
            if observer is not None:
                observer.stop()
                observer.join()


def run_server(watch: bool = False, host: str = "localhost", port: int = 8000):
    server = TurbineServer(watch=watch)
    server.run(
        host=host,
        port=port,
    )
