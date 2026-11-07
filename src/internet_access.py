import base64
import io
import json
import os
import shutil
import socket
import subprocess
import threading
import time
from collections import deque
from http.cookies import SimpleCookie, CookieError
from hmac import compare_digest
from pathlib import Path
from secrets import randbelow, token_urlsafe
from urllib.parse import parse_qs, urlsplit

import qrcode
import qrcode.image.svg
import uvicorn
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse


MAX_FAILURES = 5
MAX_TOTAL_FAILURES = 10
FAILURE_WINDOW_SECONDS = 300
LOGIN_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f7f7f8">
<title>Connect to Languages</title>
<style>
* { box-sizing: border-box; }
html { min-height: 100%; color-scheme: light; }
body { min-height: 100vh; min-height: 100dvh; margin: 0; padding: 24px;
  display: grid; place-items: center; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #1a1a1e; background: radial-gradient(ellipse at 50% 0%, #eae9ff 0%, #f7f7f8 49%, #f7f7f8 100%); }
main { width: min(100%, 440px); }
.brand { display: flex; align-items: center; gap: 11px; margin: 0 0 26px 2px;
  font-size: 15px; font-weight: 700; letter-spacing: -.02em; }
.logo { display: grid; place-items: center; width: 39px; height: 39px; border-radius: 12px;
  background: #4f46e5; color: white; font-family: Georgia, serif; font-weight: 600; font-size: 17px;
  box-shadow: 0 5px 16px #4f46e52b; }
.card { padding: clamp(26px, 7vw, 40px); border: 1px solid #e5e5ea; border-radius: 24px;
  background: #fff; box-shadow: 0 22px 55px #22203e0d, 0 3px 12px #22203e08; }
.eyebrow { margin: 0 0 12px; color: #4f46e5; font-size: 11px; font-weight: 750;
  text-transform: uppercase; letter-spacing: .13em; }
h1 { margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: clamp(31px, 8vw, 40px);
  line-height: 1.08; letter-spacing: -.035em; font-weight: 400; }
.description { margin: 15px 0 28px; color: #6e6e76; font-size: 15px; line-height: 1.6; }
label { display: block; margin-bottom: 9px; font-size: 13px; font-weight: 650; color: #33333c; }
input { display: block; width: 100%; height: 62px; border: 1px solid #d9d9e1; border-radius: 14px;
  padding: 0 18px; background: #fafafc; color: #1a1a1e; font: 600 25px/1 -apple-system, BlinkMacSystemFont, sans-serif;
  letter-spacing: .32em; text-align: center; outline: none; transition: border-color .15s, box-shadow .15s; }
input:focus { border-color: #6961e9; box-shadow: 0 0 0 4px #4f46e51a; background: white; }
button { width: 100%; min-height: 53px; margin-top: 15px; padding: 13px 20px; border: 0; border-radius: 14px;
  background: #4f46e5; color: white; font: 650 15px/1.4 -apple-system, BlinkMacSystemFont, sans-serif;
  cursor: pointer; transition: background .15s, transform .15s; }
button:hover { background: #4338ca; }
button:active { transform: translateY(1px); }
button:focus-visible { outline: 3px solid #aaa5f5; outline-offset: 3px; }
.note { margin: 19px 0 0; color: #6e6e76; font-size: 12px; line-height: 1.5; text-align: center; }
.footer { margin: 21px 0 0; color: #888891; font-size: 12px; text-align: center; }
@media (max-width: 360px) { body { padding: 18px; } .brand { margin-bottom: 18px; } }
@media (prefers-reduced-motion: reduce) { input, button { transition: none; } }
</style>
</head>
<body>
<main>
  <div class="brand"><span class="logo" aria-hidden="true">Aa</span><span>Languages</span></div>
  <div class="card">
    <p class="eyebrow">Access from another device</p>
    <h1>Welcome to<br>your words.</h1>
    <p class="description">Enter the four-digit PIN shown on your Mac.</p>
    <form action="/login" method="post">
      <label for="pin">PIN</label>
      <input id="pin" name="pin" type="password" inputmode="numeric" pattern="[0-9]{4}"
        minlength="4" maxlength="4" autocomplete="one-time-code" required autofocus>
      <button type="submit">Connect to Languages</button>
    </form>
    <p class="note">Find your PIN in Other devices on your Mac.</p>
  </div>
  <p class="footer">Your vocabulary, wherever you are.</p>
</main>
</body>
</html>"""


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
        self.pin = None
        self.session = None
        self.failures = deque()
        self.total_failures = 0
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
                      'pin': self.pin if running else None, 'pinLocked': self.total_failures >= MAX_TOTAL_FAILURES,
                      'error': self.error}
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
            pin = f"{randbelow(10000):04d}"
            session = token_urlsafe(32)
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(('127.0.0.1', 0))
                listener.listen(128)
                port = listener.getsockname()[1]
            except Exception:
                listener.close()
                raise
            self.pin = pin
            self.session = session
            self.failures.clear()
            self.total_failures = 0
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
                if self.pin != pin or self.session != session:
                    await PlainTextResponse('Access has ended.', 403)(scope, receive, send)
                    return
                cookies = SimpleCookie()
                try:
                    cookies.load(headers.get('cookie', ''))
                except CookieError:
                    cookies = SimpleCookie()
                supplied_session = cookies.get('__Host-languages_session')
                authenticated = bool(supplied_session and compare_digest(supplied_session.value.encode('utf-8'), session.encode('utf-8')))
                path = scope['path']
                if path == '/login' and scope['method'] == 'POST':
                    if headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/x-www-form-urlencoded':
                        await PlainTextResponse('Invalid request.', 400)(scope, receive, send)
                        return
                    body = b''
                    while True:
                        event = await receive()
                        if event['type'] == 'http.disconnect':
                            return
                        body += event.get('body', b'')
                        if len(body) > 1024:
                            await PlainTextResponse('Request too large.', 413)(scope, receive, send)
                            return
                        if not event.get('more_body', False):
                            break
                    try:
                        supplied = parse_qs(body.decode('utf-8'), max_num_fields=4).get('pin', [''])[0]
                    except (UnicodeDecodeError, ValueError):
                        supplied = ''
                    with self.lock:
                        now = time.monotonic()
                        while self.failures and self.failures[0] <= now - FAILURE_WINDOW_SECONDS:
                            self.failures.popleft()
                        permanently_locked = self.total_failures >= MAX_TOTAL_FAILURES
                        locked = permanently_locked or len(self.failures) >= MAX_FAILURES
                        valid = len(supplied) == 4 and supplied.isascii() and supplied.isdigit() and compare_digest(supplied, pin)
                        if not locked and not valid:
                            self.failures.append(now)
                            self.total_failures += 1
                        if not locked and valid:
                            self.failures.clear()
                    if permanently_locked:
                        await PlainTextResponse('PIN locked. Stop and restart internet access on the Mac.', 429, headers={'Cache-Control': 'no-store'})(scope, receive, send)
                    elif locked:
                        await PlainTextResponse('Too many attempts. Try again in five minutes.', 429, headers={'Cache-Control': 'no-store'})(scope, receive, send)
                    elif not valid:
                        await HTMLResponse(LOGIN_PAGE.replace('Enter the four-digit PIN shown on your Mac.', 'Incorrect PIN. Try again.'), 401, headers={'Cache-Control': 'no-store'})(scope, receive, send)
                    elif self.session != session:
                        await PlainTextResponse('Access has ended.', 403)(scope, receive, send)
                    else:
                        response = RedirectResponse('/', status_code=303, headers={'Cache-Control': 'no-store'})
                        response.set_cookie('__Host-languages_session', session, secure=True, httponly=True, samesite='strict', path='/')
                        await response(scope, receive, send)
                    return
                if not authenticated:
                    if path.startswith('/api/'):
                        await PlainTextResponse('PIN required.', 401, headers={'Cache-Control': 'no-store'})(scope, receive, send)
                    else:
                        await HTMLResponse(LOGIN_PAGE, headers={'Cache-Control': 'no-store', 'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"})(scope, receive, send)
                    return
                if path == '/login':
                    await RedirectResponse('/', status_code=303)(scope, receive, send)
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
        self.pin = None
        self.session = None
        self.failures.clear()
        self.total_failures = 0
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
