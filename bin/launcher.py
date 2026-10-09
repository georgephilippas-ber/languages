#!/usr/bin/env python3

import argparse
import socket
import sys
import threading
import time
import webbrowser
from os import environ
from os.path import abspath, dirname

DATA: str = dirname(sys.executable) if getattr(sys, "frozen", False) else dirname(abspath(__file__))
DEFAULT_PORT: int = 8100
HOST: str = "127.0.0.1"

sys.path.insert(0, dirname(DATA))


def __open_when_ready(url_: str, port_: int):
    for _ in range(300):
        try:
            with socket.create_connection((HOST, port_), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    webbrowser.open(url_)


if __name__ == "__main__":
    command_line_argument_parser_ = argparse.ArgumentParser(
        description=f"Start the packaged Languages web app, with its own data in {DATA}.")
    command_line_argument_parser_.add_argument("--port", type=int, default=DEFAULT_PORT,
                                               help=f"port (default: {DEFAULT_PORT})")
    command_line_argument_parser_.add_argument("--demo", action="store_true",
                                               help="use placeholder exercises and corrections instead of the API, "
                                                    "and do not record practice history")
    command_line_argument_parser_.add_argument("--no-browser", dest="browser", action="store_false",
                                               help="do not open the browser")
    arguments_ = command_line_argument_parser_.parse_args()

    environ["LANGUAGES_DATA"] = DATA

    import uvicorn

    from backend.app import create_app

    url_ = f"http://{HOST}:{arguments_.port}"
    print(f"Languages{' (demo mode)' if arguments_.demo else ''}: {url_}")
    print(f"Data: {DATA}")
    print("Press Ctrl+C to stop.", flush=True)

    if arguments_.browser:
        threading.Thread(target=__open_when_ready, args=(url_, arguments_.port), daemon=True).start()

    uvicorn.run(create_app(arguments_.demo), host=HOST, port=arguments_.port, log_level="warning")
