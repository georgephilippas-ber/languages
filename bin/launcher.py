#!/usr/bin/env python3
"""Bundled HTTP worker. The native app owns its lifecycle."""
import argparse
import fcntl
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.paths import data_root, initialize_data
from src.browser import open_tab

HOST = "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="Languages local server")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--no-browser", dest="browser", action="store_false")
    parser.add_argument("--check-read", action="store_true", help="Check that article extraction works and exit")
    args = parser.parse_args()
    if args.check_read:
        from trafilatura import extract
        paragraphs = ''.join(f'<p>Article extraction verification number {i} contains enough distinct words to '
                             'represent a realistic short paragraph for this diagnostic test.</p>' for i in range(20))
        extracted = extract(f'<html><body><article>{paragraphs}</article></body></html>',
                            include_comments=False, include_tables=False, favor_precision=True)
        if not extracted or 'Article extraction verification' not in extracted:
            raise SystemExit('Article extraction did not return the expected text.')
        print('Article extraction is available.')
        return
    args.browser = args.browser and os.environ.get("LANGUAGES_NO_BROWSER") != "1"
    root = data_root()
    initialize_data(root)
    url = f"http://{HOST}:{args.port}"
    with (root / f"server-{args.port}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            for _ in range(100):
                try:
                    with urlopen(url + "/api/health", timeout=0.5) as response:
                        health = json.load(response)
                    if health == {"application": "languages", "dataRoot": str(root)}:
                        if args.browser:
                            open_tab(url)
                        return
                except (OSError, ValueError):
                    pass
                time.sleep(0.1)
            raise RuntimeError("Languages is already starting. See Languages.log.")
        import uvicorn
        from backend.app import create_app
        # Reserve the port before opening a browser, so another service is never opened.
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((HOST, args.port))
            listener.listen(128)
            if args.browser:
                def ready():
                    for _ in range(300):
                        try:
                            with urlopen(url + "/api/health", timeout=0.5) as response:
                                if json.load(response).get("application") == "languages":
                                    open_tab(url)
                                    return
                        except (OSError, ValueError):
                            time.sleep(0.1)
                threading.Thread(target=ready, daemon=True).start()
            app = create_app(shutdown=lambda: setattr(server, "should_exit", True))
            server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=args.port,
                                                  timeout_graceful_shutdown=5, log_level="warning"))
            server.run(sockets=[listener])


if __name__ == "__main__":
    main()
