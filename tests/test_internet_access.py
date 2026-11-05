import json
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from src.internet_access import InternetAccess


def test_remote_management_must_be_local():
    with TestClient(create_app(), base_url='http://127.0.0.1') as client:
        assert client.get('/api/internet').status_code == 200
        assert client.post('/api/internet/start', headers={'origin': 'https://example.com'}).status_code == 403
        assert client.post('/api/internet/stop', headers={'host': 'example.com'}).status_code == 403


def test_missing_agent_does_not_start(monkeypatch):
    monkeypatch.setattr('src.internet_access.agent_path', lambda: None)
    access = InternetAccess(create_app())
    with pytest.raises(ValueError, match='not installed'):
        access.start()
    assert not access.status()['active']


@pytest.mark.browser
def test_protected_upstream_auth_and_revocation(tmp_path, monkeypatch):
    fake = tmp_path / 'fake-ngrok'
    fake.write_text('#!/usr/bin/env python3\nimport json,time\nprint(json.dumps({"msg":"started tunnel","url":"https://example.ngrok-free.app"}),flush=True)\nwhile True: time.sleep(1)\n')
    fake.chmod(0o700)
    monkeypatch.setattr('src.internet_access.agent_path', lambda: str(fake))
    access = InternetAccess(create_app())
    try:
        access.start()
        for _ in range(50):
            status = access.status()
            if status['active']:
                break
            time.sleep(.1)
        assert status['active'] and status['url'] == 'https://example.ngrok-free.app'
        assert status['qr'].startswith('data:image/svg+xml;base64,')
        upstream = access.process.args[2]
        headers = {'Host': 'example.ngrok-free.app'}
        with httpx.Client(trust_env=False, timeout=3, headers=headers) as client:
            for _ in range(50):
                try:
                    response = client.get(upstream + '/api/meta')
                    break
                except httpx.ConnectError:
                    time.sleep(.1)
            assert response.status_code == 401
            assert len(status['pin']) == 4 and status['pin'].isdigit()
            assert client.get(upstream + '/').status_code == 200
            wrong = '0000' if status['pin'] != '0000' else '0001'
            assert client.post(upstream + '/login', data={'pin': wrong}).status_code == 401
            login = client.post(upstream + '/login', data={'pin': status['pin']})
            assert login.status_code == 303
            cookie = login.headers['set-cookie']
            assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
            headers = {'Cookie': cookie.split(';', 1)[0]}
            assert client.get(upstream + '/api/meta', headers=headers).status_code == 200
            assert client.get(upstream + '/api/internet', headers=headers).status_code == 403
            assert client.get(upstream + '/api/meta', headers={**headers, 'Host': 'evil.example'}).status_code == 403
            assert client.get(upstream + '/api/settings/api-key', headers=headers).status_code == 403
            assert client.post(upstream + '/api/quiz', headers={**headers, 'Origin': 'https://evil.example'}).status_code == 403
            access.stop()
            try:
                assert client.get(upstream + '/api/meta', headers=headers).status_code in (401, 403)
            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
                pass
    finally:
        access.stop()


@pytest.mark.browser
def test_pin_attempts_are_limited(tmp_path, monkeypatch):
    fake = tmp_path / 'fake-ngrok'
    fake.write_text('#!/usr/bin/env python3\nimport json,time\nprint(json.dumps({"msg":"started tunnel","url":"https://example.ngrok-free.app"}),flush=True)\nwhile True: time.sleep(1)\n')
    fake.chmod(0o700)
    monkeypatch.setattr('src.internet_access.agent_path', lambda: str(fake))
    access = InternetAccess(create_app())
    try:
        access.start()
        for _ in range(50):
            status = access.status()
            if status['active']:
                break
            time.sleep(.1)
        upstream = access.process.args[2]
        wrong = '0000' if status['pin'] != '0000' else '0001'
        with httpx.Client(trust_env=False, timeout=3, headers={'Host': 'example.ngrok-free.app'}) as client:
            for _ in range(5):
                assert client.post(upstream + '/login', data={'pin': wrong}).status_code == 401
            assert client.post(upstream + '/login', data={'pin': status['pin']}).status_code == 429
            with access.lock:
                access.failures.clear()
            for _ in range(5):
                assert client.post(upstream + '/login', data={'pin': wrong}).status_code == 401
            assert client.post(upstream + '/login', data={'pin': status['pin']}).status_code == 429
            assert access.status()['pinLocked'] is True
    finally:
        access.stop()
