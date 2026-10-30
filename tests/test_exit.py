from threading import Event
from fastapi.testclient import TestClient
from backend.app import create_app


def test_exit_is_local_token_protected_and_invokes_shutdown():
    stopped = Event()
    with TestClient(create_app(shutdown=stopped.set), base_url="http://127.0.0.1") as client:
        token = client.get('/api/lifecycle').json()['exitToken']
        assert token
        assert client.post('/api/exit').status_code == 403
        assert client.post('/api/exit', headers={'X-Languages-Exit': token, 'Origin': 'https://other.example'}).status_code == 403
        assert client.get('/api/lifecycle', headers={'Host': 'other.example'}).status_code == 403
        assert not stopped.is_set()
        assert client.post('/api/exit', headers={'X-Languages-Exit': token}).json() == {'status': 'quitting'}
        assert stopped.wait(2)


def test_development_factory_does_not_offer_exit():
    with TestClient(create_app(), base_url="http://127.0.0.1") as client:
        assert client.get('/api/lifecycle').json()['exitToken'] is None
        assert client.post('/api/exit').status_code == 409
