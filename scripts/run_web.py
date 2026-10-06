#!/usr/local/bin/python3

import argparse
import socket
import sys
import threading
import time
import webbrowser
from os import environ
from os.path import abspath, dirname, isfile, join

ROOT: str = dirname(dirname(abspath(__file__)))
sys.path.insert(0, ROOT)

import uvicorn

from backend.app import DEMO_VARIABLE, FRONTEND_DIST

DEFAULT_HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 8000
LOCAL_HOSTS: tuple = ("127.0.0.1", "localhost", "::1")


def __announce_when_ready(url_: str, host_: str, port_: int, browser_: bool):
    for _ in range(150):
        try:
            with socket.create_connection((host_ if host_ not in ("0.0.0.0", "::") else "127.0.0.1", port_),
                                          timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    print(f"Running at {url_} (open this address again if you close the browser window).", flush=True)
    if browser_:
        webbrowser.open(url_)


if __name__ == "__main__":
    command_line_argument_parser_ = argparse.ArgumentParser(
        description="Start the Languages web app: the API and the built frontend, on one local server.",
        epilog="examples:\n"
               "  %(prog)s                 start on http://127.0.0.1:8000 and open the browser\n"
               "  %(prog)s --demo          placeholder exercises, without calling the API or recording history\n"
               "  %(prog)s --port 8080     use another port\n"
               "  %(prog)s --reload        restart the server when Python files change (for development)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    command_line_argument_parser_.add_argument("--host", default=DEFAULT_HOST,
                                               help=f"address to listen on (default: {DEFAULT_HOST}, this computer "
                                                    f"only)")
    command_line_argument_parser_.add_argument("--port", type=int, default=DEFAULT_PORT,
                                               help=f"port (default: {DEFAULT_PORT})")
    command_line_argument_parser_.add_argument("--demo", action="store_true",
                                               help="use placeholder exercises and corrections instead of the API, "
                                                    "and do not record practice history")
    command_line_argument_parser_.add_argument("--no-browser", dest="browser", action="store_false",
                                               help="do not open the browser")
    command_line_argument_parser_.add_argument("--reload", action="store_true",
                                               help="restart when the Python code changes")
    arguments_ = command_line_argument_parser_.parse_args()

    if arguments_.demo:
        environ[DEMO_VARIABLE] = "1"
    url_ = f"http://{'127.0.0.1' if arguments_.host in ('0.0.0.0', '::') else arguments_.host}:{arguments_.port}"

    print(f"Languages{' (demo mode)' if arguments_.demo else ''}: {url_}")
    if not isfile(join(FRONTEND_DIST, "index.html")):
        print("The frontend has not been built yet: run 'npm install' and 'npm run build' in frontend/ first.")
    if arguments_.host not in LOCAL_HOSTS:
        print(f"Warning: listening on {arguments_.host}, so other devices on your network can use this server "
              f"and your OpenAI API key.")
    print("Press Ctrl+C to stop.", flush=True)

    threading.Thread(target=__announce_when_ready, args=(url_, arguments_.host, arguments_.port, arguments_.browser),
                     daemon=True).start()

    uvicorn.run("backend.app:create_app", factory=True, host=arguments_.host, port=arguments_.port, app_dir=ROOT,
                reload=arguments_.reload, reload_dirs=[join(ROOT, "backend"), join(ROOT, "src")] if arguments_.reload
                else None, log_level="warning")
