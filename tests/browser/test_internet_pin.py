import ssl
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from playwright.sync_api import sync_playwright, expect

from backend.app import create_app
from src.internet_access import InternetAccess


def test_pin_page_works_in_webkit_without_real_ngrok(tmp_path, monkeypatch):
    fake = tmp_path / 'fake-ngrok'
    fake.write_text('#!/usr/bin/env python3\nimport json,time\nprint(json.dumps({"msg":"started tunnel","url":"https://example.ngrok-free.app"}),flush=True)\nwhile True: time.sleep(1)\n')
    fake.chmod(0o700)
    monkeypatch.setattr('src.internet_access.agent_path', lambda: str(fake))
    access = InternetAccess(create_app())
    server = None
    try:
        access.start()
        for _ in range(50):
            status = access.status()
            if status['active']:
                break
            time.sleep(.1)
        assert status['active']
        upstream = access.process.args[2]
        key, cert = tmp_path / 'key.pem', tmp_path / 'cert.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-keyout', str(key), '-out', str(cert)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        class Proxy(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.forward()
            def do_POST(self):
                self.forward()
            def forward(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                headers = {key: value for key, value in self.headers.items()
                           if key.lower() not in ('content-length', 'accept-encoding', 'connection')}
                with httpx.Client(trust_env=False, timeout=3, follow_redirects=False) as client:
                    response = client.request(self.command, upstream + self.path, headers=headers, content=body)
                self.send_response(response.status_code)
                for key, value in response.headers.items():
                    if key.lower() not in ('transfer-encoding', 'content-length', 'content-encoding', 'connection'):
                        self.send_header(key, value)
                self.send_header('Content-Length', str(len(response.content)))
                self.end_headers()
                self.wfile.write(response.content)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Proxy)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with access.lock:
            access.url = f'https://127.0.0.1:{server.server_port}'
        with sync_playwright() as playwright:
            browser = playwright.webkit.launch()
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.goto(access.url)
            expect(page.get_by_label('PIN', exact=True)).to_be_visible()
            page.get_by_label('PIN', exact=True).fill(status['pin'])
            page.get_by_role('button', name='Connect').click()
            expect(page.get_by_role('button', name='Languages menu')).to_be_visible(timeout=10000)
            assert any(cookie['name'] == '__Host-languages_session' and cookie['secure'] and cookie['httpOnly']
                       for cookie in context.cookies())
            context.close()
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        access.stop()
