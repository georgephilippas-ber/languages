import socket
from os import environ, stat

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from src import api_key, models, openai_integration

KEY: str = "sk-test-0123456789abcdefWXYZ"


def __no_network(*args_, **kwargs_):
    raise AssertionError("the API key must not leave this computer")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv(api_key.KEY_NAME, raising=False)
    monkeypatch.setattr(socket.socket, "connect", __no_network)
    monkeypatch.setattr(socket, "create_connection", __no_network)
    api_key.env_path().unlink(missing_ok=True)
    with TestClient(create_app(), base_url="http://127.0.0.1") as client_:
        yield client_
    api_key.env_path().unlink(missing_ok=True)
    environ.pop(api_key.KEY_NAME, None)


def test_status_reports_a_missing_key(client):
    assert client.get("/api/settings/api-key").json() == {"configured": False, "hint": None, "source": None}


def test_saving_is_local_keeps_other_settings_and_replaces_the_old_key(client, monkeypatch, fake_openai):
    api_key.env_path().write_text("export OPENAI_API_KEY=sk-old\nOTHER=1", encoding="utf-8")
    reset_ = []
    monkeypatch.setattr(api_key, "reset_openai_client", lambda: reset_.append("client"))
    monkeypatch.setattr(api_key, "reset_models", lambda: reset_.append("models"))

    response_ = client.put("/api/settings/api-key", json={"key": f'  "{KEY}" '})

    assert response_.json() == {"configured": True, "hint": "WXYZ", "source": "file"}
    assert KEY not in response_.text
    assert fake_openai.calls == []
    assert api_key.env_path().read_text(encoding="utf-8") == f"OTHER=1\nOPENAI_API_KEY={KEY}\n"
    assert stat(api_key.env_path()).st_mode & 0o777 == 0o600
    assert environ[api_key.KEY_NAME] == KEY
    assert reset_ == ["client", "models"]
    assert not list(api_key.env_path().parent.glob(".env-*.tmp"))


def test_malformed_keys_are_refused_without_echoing_them(client):
    for key_ in ["", "not-a-key", "sk-abc", f"{KEY}\nOTHER=1"]:
        response_ = client.put("/api/settings/api-key", json={"key": key_})
        assert response_.status_code == 400
        assert not key_ or key_ not in response_.text
    assert not api_key.env_path().exists()


def test_only_local_same_origin_requests_may_see_or_change_the_key(client):
    assert client.put("/api/settings/api-key", json={"key": KEY},
                      headers={"Origin": "https://other.example"}).status_code == 403
    with TestClient(create_app()) as remote_:
        assert remote_.put("/api/settings/api-key", json={"key": KEY}).status_code == 403
        assert remote_.get("/api/settings/api-key").status_code == 403
    assert not api_key.env_path().exists()


def test_resets_drop_the_cached_client_and_models(monkeypatch):
    monkeypatch.setattr(models, "_" + "_cached_models", ["gpt-old"], raising=False)
    models.reset_models()
    assert models.available_models() != ["gpt-old"]
    openai_integration.reset_openai_client()
