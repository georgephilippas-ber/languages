import base64
import binascii
import io
import json
import os
import shutil
import socket
import subprocess
import threading
import time
from hmac import compare_digest
from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import urlsplit

import qrcode
import qrcode.image.svg
import uvicorn
from starlette.responses import PlainTextResponse


def agent_path():
    for path in (shutil.which('ngrok'), '/opt/homebrew/bin/ngrok', '/usr/local/bin/ngrok'):
        if path and Path(path).is_file() and os.access(path, os.X_OK):
            return path
    return None


def qr_image(url):
    output = io.BytesIO()
    qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=4).save(output)
    return 'data:image/svg+xml;base64,' + base64.b64encode(output.getvalue()).decode()


class InternetAccess:
    def __init__(self, app):
        self.app = app
        self.lock = threading.RLock()
        self.process = None
        self.server = None
        self.thread = None
        self.password = None
        self.url = None
        self.error = None
        self.started_at = 0.0

    def status(self):
        with self.lock:
            running = self.process is not None and self.process.poll() is None
            if running and self.url is None and time.monotonic() - self.started_at > 30:
                self._stop_locked()
                self.error = 'ngrok did not connect. Check your network and account configuration.'
                running = False
            if not running and self.process is not None:
                self._stop_locked()
                self.error = 'ngrok stopped. Check its installation and account configuration.'
            result = {'installed': agent_path() is not None, 'active': running and self.url is not None,
                      'starting': running and self.url is None, 'url': self.url if running else None,
                      'username': 'languages' if running else None,
                      'password': self.password if running else None, 'error': self.error}
            if result['active']:
                result['qr'] = qr_image(self.url)
            return result

    def start(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return self.status()
            self._stop_locked()
            executable = agent_path()
            if not executable:
                raise ValueError('ngrok is not installed. Install it and configure your authtoken first.')
            password = token_urlsafe(18)
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(('127.0.0.1', 0))
                listener.listen(128)
                port = listener.getsockname()[1]
            except Exception:
                listener.close()
                raise
            self.password = password
            self.error = None

            async def protected(scope, receive, send):
                if scope['type'] != 'http':
                    await PlainTextResponse('Forbidden', 403)(scope, receive, send)
                    return
                headers = {k.decode('latin1').lower(): v.decode('latin1') for k, v in scope['headers']}
                origin = headers.get('origin')
                host = headers.get('host', '')
                expected_host = urlsplit(self.url).netloc if self.url else ''
                if (not expected_host or host != expected_host or (origin and origin != 'https://' + host)
                        or headers.get('sec-fetch-site') == 'cross-site'):
                    await PlainTextResponse('Forbidden', 403)(scope, receive, send)
                    return
                auth = headers.get('authorization', '')
                try:
                    supplied = base64.b64decode(auth[6:], validate=True).decode('utf-8') if auth.startswith('Basic ') else ''
                except (binascii.Error, UnicodeDecodeError):
                    supplied = ''
                if self.password != password or not compare_digest(supplied.encode('utf-8'), ('languages:' + password).encode('utf-8')):
                    await PlainTextResponse('Authentication required', 401, headers={'WWW-Authenticate': 'Basic realm="Languages", charset="UTF-8"', 'Cache-Control': 'no-store'})(scope, receive, send)
                    return
                if scope['path'].startswith(('/api/device', '/api/internet', '/api/settings', '/api/lifecycle', '/api/exit', '/api/health')):
                    await PlainTextResponse('Available only on the Mac.', 403)(scope, receive, send)
                    return
                await self.app(scope, receive, send)

            server = uvicorn.Server(uvicorn.Config(protected, log_level='warning', lifespan='off'))
            server.install_signal_handlers = lambda: None
            thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
            self.server = server
            self.thread = thread
            thread.start()
            try:
                process = subprocess.Popen([executable, 'http', f'http://127.0.0.1:{port}', '--inspect=false',
                                            '--log=stdout', '--log-format=json'], stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, bufsize=1)
            except Exception:
                self._stop_locked()
                raise
            self.process = process
            self.started_at = time.monotonic()
            threading.Thread(target=self._read_logs, args=(process,), daemon=True).start()
            return self.status()

    def _read_logs(self, process):
        for line in process.stdout:
            try:
                record = json.loads(line)
                url = record.get('url', '')
                parsed = urlsplit(url)
                if parsed.scheme == 'https' and parsed.hostname and record.get('msg') == 'started tunnel':
                    with self.lock:
                        if self.process is process:
                            self.url = url
            except (ValueError, TypeError, AttributeError):
                pass

    def _stop_locked(self):
        self.password = None
        self.url = None
        if self.server:
            self.server.should_exit = True
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None
        self.server = None
        self.thread = None

    def stop(self):
        with self.lock:
            self._stop_locked()
            self.error = None
            return self.status()
