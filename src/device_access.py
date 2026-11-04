import base64
import io
import socket
import subprocess
import threading
from hmac import compare_digest
from secrets import token_urlsafe

import qrcode
import qrcode.image.svg
import uvicorn
from starlette.responses import PlainTextResponse, RedirectResponse


class DeviceAccess:
    def __init__(self, app):
        self.app = app
        self.lock = threading.RLock()
        self.server = None
        self.thread = None
        self.token = None
        self.url = None
        self.awake = None
        self.awake_minutes = 0

    def status(self):
        with self.lock:
            if self.awake and self.awake.poll() is not None:
                self.awake = None
                self.awake_minutes = 0
            active = self.server is not None and self.thread is not None and self.thread.is_alive()
            result = {"active": active, "url": self.url if active else None,
                      "awakeMinutes": self.awake_minutes}
            if active:
                image = qrcode.make(self.url, image_factory=qrcode.image.svg.SvgPathImage, border=4)
                output = io.BytesIO()
                image.save(output)
                result["qr"] = "data:image/svg+xml;base64," + base64.b64encode(output.getvalue()).decode()
            return result

    def start(self):
        with self.lock:
            if self.server and self.thread and self.thread.is_alive():
                return self.status()
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("192.0.2.1", 80))
                address = probe.getsockname()[0]
            if address.startswith("127."):
                raise ValueError("No local network address is available.")
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((address, 0))
                listener.listen(128)
            except Exception:
                listener.close()
                raise
            host = f"{address}:{listener.getsockname()[1]}"
            token = token_urlsafe(32)
            self.token = token
            self.url = f"http://{host}/join/{token}"

            async def shared(scope, receive, send):
                if scope["type"] != "http":
                    await PlainTextResponse("Forbidden", 403)(scope, receive, send)
                    return
                headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
                origin = headers.get("origin")
                if headers.get("host") != host or (origin and origin != f"http://{host}"):
                    await PlainTextResponse("Forbidden", 403)(scope, receive, send)
                    return
                path = scope["path"]
                if path == f"/join/{token}" and self.token == token:
                    response = RedirectResponse("/", status_code=303)
                    response.set_cookie("languages_device", token, httponly=True, samesite="strict", path="/")
                    response.headers["Cache-Control"] = "no-store"
                    response.headers["Referrer-Policy"] = "no-referrer"
                    await response(scope, receive, send)
                    return
                cookie = next((part.strip().partition("=")[2] for part in headers.get("cookie", "").split(";")
                               if part.strip().startswith("languages_device=")), "")
                if self.token != token or not compare_digest(cookie, token) or path.startswith(("/api/device", "/api/settings", "/api/lifecycle", "/api/exit")):
                    await PlainTextResponse("Device access is not authorized.", 403)(scope, receive, send)
                    return
                await self.app(scope, receive, send)

            server = uvicorn.Server(uvicorn.Config(shared, log_level="warning", lifespan="off"))
            server.install_signal_handlers = lambda: None
            self.server = server
            self.thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
            self.thread.start()
            return self.status()

    def revoke(self):
        with self.lock:
            self.token = None
            self.url = None
            if self.server:
                self.server.should_exit = True
            self.server = None
            self.thread = None
            return self.status()

    def keep_awake(self, minutes):
        if minutes not in (0, 30, 60, 120):
            raise ValueError("Choose 30 minutes, 1 hour, 2 hours, or off.")
        with self.lock:
            if self.awake and self.awake.poll() is None:
                self.awake.terminate()
                self.awake.wait(timeout=5)
            self.awake = None
            self.awake_minutes = 0
            if minutes:
                self.awake = subprocess.Popen(["/usr/bin/caffeinate", "-dims", "-t", str(minutes * 60)],
                                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL)
                self.awake_minutes = minutes
            return self.status()

    def close(self):
        self.revoke()
        self.keep_awake(0)
