from os import stat
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from src import api_key, elevenlabs

OPENAI = 'sk-test-0123456789abcdefWXYZ'
ELEVEN = 'sk_test_0123456789abcdef1234'


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('ELEVENLABS_API_KEY', raising=False)
    api_key.env_path().unlink(missing_ok=True)
    elevenlabs.key_path().unlink(missing_ok=True)
    with TestClient(create_app(), base_url='http://127.0.0.1') as client:
        yield client
    api_key.env_path().unlink(missing_ok=True)
    elevenlabs.key_path().unlink(missing_ok=True)


def test_keys_are_independent_and_private(client):
    assert client.put('/api/settings/api-key', json={'key': OPENAI}).status_code == 200
    original_openai = api_key.env_path().read_text()
    response = client.put('/api/settings/elevenlabs-key', json={'key': ELEVEN})
    assert response.json() == {'configured': True, 'hint': '1234', 'source': 'file'}
    assert ELEVEN not in response.text
    assert api_key.env_path().read_text() == original_openai
    assert ELEVEN not in original_openai and OPENAI not in elevenlabs.key_path().read_text()
    assert stat(elevenlabs.key_path()).st_mode & 0o777 == 0o600
    assert client.get('/api/settings/api-key').json()['hint'] == 'WXYZ'
    assert client.put('/api/settings/api-key', json={'key': 'sk-other-0123456789abcdef9999'}).status_code == 200
    assert client.get('/api/settings/elevenlabs-key').json()['hint'] == '1234'
    assert client.put('/api/settings/elevenlabs-key', json={'key': 'invalid'}).status_code == 400
    assert client.put('/api/settings/elevenlabs-key', json={'key': ELEVEN}, headers={'Origin': 'https://other.example'}).status_code == 403
    with TestClient(create_app()) as remote:
        assert remote.get('/api/settings/elevenlabs-key').status_code == 403
        assert remote.put('/api/settings/elevenlabs-key', json={'key': ELEVEN}).status_code == 403


def test_speech_uses_account_voice_and_never_exposes_key(client, monkeypatch):
    assert client.post('/api/speech', json={'text': 'Hallo Welt', 'language': 'DE'}).status_code == 404
    assert client.put('/api/settings/elevenlabs-key', json={'key': ELEVEN}).status_code == 200
    calls = []
    def request(request):
        calls.append(request)
        assert request.headers['xi-api-key'] == ELEVEN
        if request.method == 'GET':
            assert request.url.path == '/v2/voices' and request.url.params['language'] == 'de'
            return httpx.Response(200, json={'voices': [{'voice_id': 'GermanVoice123'}]})
        assert request.url.path == '/v1/text-to-speech/GermanVoice123'
        assert b'eleven_flash_v2_5' in request.content and b'"language_code":"de"' in request.content
        return httpx.Response(200, content=b'fake audio', headers={'content-type': 'audio/mpeg'})
    real_client = httpx.Client
    monkeypatch.setattr(elevenlabs.httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(request)))
    response = client.post('/api/speech', json={'text': 'Hallo Welt', 'language': 'DE'})
    assert response.status_code == 200 and response.content == b'fake audio'
    assert response.headers['cache-control'] == 'no-store'
    assert ELEVEN not in response.text and OPENAI not in response.text
    assert len(calls) == 2


def test_speech_and_key_settings_do_not_depend_on_selected_openai_model(client, monkeypatch):
    monkeypatch.setattr('backend.app.available_models', lambda: (_ for _ in ()).throw(AssertionError('OpenAI must not be consulted')))
    headers = {'X-OpenAI-Model': 'unavailable-model'}
    assert client.put('/api/settings/elevenlabs-key', json={'key': ELEVEN}, headers=headers).status_code == 200
    assert client.get('/api/settings/elevenlabs-key', headers=headers).status_code == 200
    monkeypatch.setattr(elevenlabs, 'synthesize', lambda text, language: b'audio')
    assert client.post('/api/speech', json={'text': 'bonjour', 'language': 'FR'}, headers=headers).content == b'audio'


def test_missing_elevenlabs_voice_permission_is_reported_safely(client, monkeypatch):
    request = httpx.Request('GET', 'https://api.elevenlabs.io/v2/voices', headers={'xi-api-key': ELEVEN})
    response = httpx.Response(401, request=request, json={'detail': {'status': 'missing_permissions', 'message': ELEVEN}})
    def fail(*args):
        raise httpx.HTTPStatusError('secret should not leak', request=request, response=response)
    monkeypatch.setattr(elevenlabs, 'synthesize', fail)
    result = client.post('/api/speech', json={'text': 'bonjour', 'language': 'FR'})
    assert result.status_code == 503
    assert result.json()['detail'] == 'ElevenLabs key needs Voices read permission.'
    assert ELEVEN not in result.text
