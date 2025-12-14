import http.server
import socketserver
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import multiprocessing
from turbines.builder import build_site


def start_watching():
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
                        build_site()
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


def run_server():
    # serve the directory at ./site using uvicorn

    PORT = 8000
    DIRECTORY = os.path.join(os.getcwd(), ".site")

    os.chdir(DIRECTORY)
    Handler = http.server.SimpleHTTPRequestHandler

    print(f"Serving '{DIRECTORY}' at http://localhost:{PORT} ...")
    print("Do not use in production!")

    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down server...")
            httpd.shutdown()
