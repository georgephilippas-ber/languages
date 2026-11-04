import socket
import time
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from src.device_access import DeviceAccess


def test_device_management_requires_local_same_origin():
    with TestClient(create_app(), base_url='http://127.0.0.1') as client:
        assert client.get('/api/device').json()['active'] is False
        assert client.post('/api/device/awake/1').status_code == 400
        assert client.post('/api/device/start', headers={'origin': 'https://example.com'}).status_code == 403
        assert client.post('/api/device/revoke', headers={'host': 'attacker.example'}).status_code == 403


def test_caffeinate_options_and_cleanup(monkeypatch):
    class Process:
        def __init__(self, args, **kwargs):
            self.args = args
            self.dead = False
        def poll(self):
            return 0 if self.dead else None
        def terminate(self):
            self.dead = True
        def wait(self, timeout):
            return 0
    monkeypatch.setattr('src.device_access.subprocess.Popen', Process)
    access = DeviceAccess(None)
    assert access.keep_awake(30)['awakeMinutes'] == 30
    previous = access.awake
    assert access.keep_awake(120)['awakeMinutes'] == 120
    assert previous.dead
    assert access.keep_awake(180)['awakeMinutes'] == 180
    assert access.awake.args[-1] == str(3 * 60 * 60)
    previous = access.awake
    access.close()
    assert previous.dead
    with pytest.raises(ValueError):
        access.keep_awake(45)


@pytest.mark.browser
def test_sharing_authentication_and_revocation():
    access = DeviceAccess(create_app())
    try:
        status = access.start()
        assert status['active'] and status['qr'].startswith('data:image/svg+xml;base64,')
        url = status['url']
        root = f'{urlsplit(url).scheme}://{urlsplit(url).netloc}'
        assert status['localUrl'] == root
        assert status['localQr'].startswith('data:image/svg+xml;base64,')
        with httpx.Client(trust_env=False, timeout=3) as client:
            for _ in range(50):
                try:
                    response = client.get(root + '/api/meta')
                    break
                except httpx.ConnectError:
                    time.sleep(.1)
            assert response.status_code == 200
            local = client.get(root, follow_redirects=False)
            assert local.status_code == 200
            assert not local.is_redirect and not client.cookies
            assert client.get(root + '/api/meta').status_code == 200
            client.cookies.clear()
            assert client.get(url, follow_redirects=False).status_code == 303
            assert client.get(root + '/api/meta').status_code == 200
            client.cookies.clear()
            assert client.get(root + '/api/meta').status_code == 200
            assert client.get(root + '/api/device').status_code == 403
            assert client.post(root + '/api/quiz', headers={'Origin': 'https://example.com'}).status_code == 403
            access.revoke()
            try:
                response = client.get(root + '/api/meta')
                assert response.status_code == 403
            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
                pass
    finally:
        access.close()
