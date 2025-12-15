import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import multiprocessing
from turbines.builder import Builder


def start_watching(builder: Builder):
    def watch():
        path = os.path.join(os.getcwd())
        print(f"Watching for changes in {path} ...")

        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._last_built = 0
                self._debounce_seconds = 1

            # on save, rebuild the site
            def on_modified(self, event):
                if not event.is_directory:
                    now = time.time()
                    if now - self._last_built > self._debounce_seconds:
                        print(f"Rebuilding site due to change in {event.src_path} ...")
                        # call build_site from builder.py
                        builder.reload()
                        self._last_built = now

        event_handler = ChangeHandler()
        observer = Observer()
        observer.schedule(event_handler, path=path, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    p = multiprocessing.Process(target=watch)
    p.start()
    return p


import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.httpserver


CLIENTS = []


def notify_reload():
    print("Notifying clients to reload...", CLIENTS, id(CLIENTS))
    for client in list(CLIENTS):
        print("Notifying client to reload:", client)
        try:
            client.write_message("reload")
            print("Reload message sent to client:", client)
        except:
            CLIENTS.remove(client)
            print("Removed disconnected client:", client)


class ChangeHandler(FileSystemEventHandler):
    def set_loop(self, loop):
        self.loop = loop

    def on_modified(self, event):
        if str(event.src_path).endswith(".html"):
            print(
                f"File changed: {event.src_path}, notifying clients to reload...",
                id(CLIENTS),
            )
            self.loop.add_callback(notify_reload)
            print("Notification scheduled.")


class LiveReloadWebSocketHandler(tornado.websocket.WebSocketHandler):

    def open(self, *args, **kwargs):
        print("LiveReload client connected", id(CLIENTS))
        CLIENTS.append(self)

        print("Current clients:", CLIENTS)

    def on_close(self):
        print("LiveReload client disconnected")
        CLIENTS.remove(self)

    def on_message(self, message: str | bytes):
        print(f"Received message from client: {message}")
        pass

    def check_origin(self, origin: str) -> bool:
        return True  # Allow connections from any origin


class StaticFileHandlerWithReload(tornado.web.StaticFileHandler):
    async def get(self, path, include_body=True):
        # Serve /index.html for root or empty path
        if path == "" or path == "/":
            path = "index.html"
        absolute_path = self.get_absolute_path(self.root, path)
        if path.endswith(".html") and os.path.exists(absolute_path):
            print("Injecting LiveReload script into", path)
            with open(absolute_path, "r", encoding="utf-8") as f:
                html = f.read()
            # Inject the reload script before </body> if present, else at the end
            if "</body>" in html:
                html = html.replace("</body>", RELOAD_SCRIPT + "</body>")
            else:
                html += RELOAD_SCRIPT
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

    def patch_builder_for_reload(self):
        orig_reload = self.builder.reload

        def patched_reload():
            orig_reload()
            print("Notifying LiveReload clients to reload...", CLIENTS)
            for client in CLIENTS:
                print("Sending reload message to client", client)
                client.write_message("reload")

        self.builder.reload = patched_reload

    def serve(self):
        PORT = 8000
        os.chdir(self.builder.build_path)
        print(f"Serving '{self.builder.build_path}' at http://localhost:{PORT} ...")
        print("Do not use in production!")

        self.app = tornado.web.Application(
            [
                (r"/_turbines/livereload", LiveReloadWebSocketHandler),
                (
                    r"/(.*)",
                    StaticFileHandlerWithReload,
                    {"path": self.builder.build_path},
                ),
            ]
        )
        server = tornado.httpserver.HTTPServer(self.app)
        server.listen(PORT, address="127.0.0.1")
        # tornado.ioloop.IOLoop.current().start()

    def run(self):
        loop = tornado.ioloop.IOLoop.current()
        if self.watch:

            observer = Observer()
            handler = ChangeHandler()
            handler.set_loop(loop)
            observer.schedule(handler, path=os.path.join(os.getcwd()), recursive=True)
            observer.start()
        try:
            self.serve()
            tornado.ioloop.IOLoop.current().start()
        finally:
            observer.stop()
            observer.join()


def run_server(watch: bool = False):
    server = TurbineServer(watch=watch)
    server.run()


RELOAD_SCRIPT = """
<script>
    const ws = new WebSocket("ws://localhost:8000/_turbines/livereload");
    ws.onmessage = (event) => {
        if (event.data === "reload") {
            console.log("Reload message received, reloading page...");
            window.location.reload();
        }
    };
    ws.onopen = () => {
        console.log("LiveReload WebSocket connection established.");
    };
    ws.onclose = () => {
        console.log("LiveReload WebSocket connection closed.");
    };
</script>
"""
