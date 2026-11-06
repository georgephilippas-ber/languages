"""Independent ElevenLabs credentials and speech generation."""
import hashlib
import os
import re
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Optional

import httpx
from dotenv import dotenv_values
from src.domain import DATA_ROOT

KEY_NAME = 'ELEVENLABS_API_KEY'
KEY_PATTERN = re.compile(r'^[A-Za-z0-9_-]{10,512}$')
VOICE_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
VOICE_TTL = 3600
# ElevenLabs' documented quickstart voice also works with a TTS-only restricted key.
FALLBACK_VOICE_ID = 'JBFqnCBsd6RMkjVDRZzb' 
_lock = Lock()
_voices: dict[tuple[str, str], tuple[float, str]] = {}


def key_path() -> Path:
    return Path(DATA_ROOT) / '.elevenlabs.env'


def _file_key() -> Optional[str]:
    path = key_path()
    return (dotenv_values(path).get(KEY_NAME) or None) if path.is_file() else None


def current_key() -> Optional[str]:
    return _file_key() or os.environ.get(KEY_NAME) or None


def key_status() -> dict:
    file_key = _file_key()
    key = file_key or os.environ.get(KEY_NAME)
    return {'configured': bool(key), 'hint': key[-4:] if key else None,
            'source': ('file' if file_key else 'environment') if key else None}


def normalize_key(value: str) -> str:
    value = value.strip().strip("\"'")
    if not KEY_PATTERN.fullmatch(value):
        raise ValueError('This does not look like an ElevenLabs API key')
    return value


def save_key(value: str) -> None:
    path = key_path()
    temporary = None
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, prefix='.elevenlabs-', suffix='.tmp', delete=False) as f:
                temporary = Path(f.name)
                f.write(f'{KEY_NAME}={value}\n')
                f.flush()
                os.fsync(f.fileno())
            temporary.chmod(0o600)
            os.replace(temporary, path)
            _voices.clear()
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def _choose_voice(client: httpx.Client, key: str, language: str) -> str:
    cache_key = (hashlib.sha256(key.encode()).hexdigest(), language)
    with _lock:
        cached = _voices.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    headers = {'xi-api-key': key}
    # Voices returned here are those the account can actually access; do not rely on expiring default IDs.
    voice_id = None
    for params in ({'language': language, 'page_size': 30}, {'page_size': 30}):
        response = client.get('https://api.elevenlabs.io/v2/voices', headers=headers, params=params)
        if response.status_code in (401, 403):
            try:
                detail = response.json().get('detail', {})
                if isinstance(detail, dict) and detail.get('status') == 'missing_permissions':
                    voice_id = FALLBACK_VOICE_ID
                    break
            except (ValueError, AttributeError):
                pass
        response.raise_for_status()
        body = response.json()
        voices = body.get('voices', []) if isinstance(body, dict) else []
        voice_id = next((voice['voice_id'] for voice in voices if isinstance(voice, dict)
                         and isinstance(voice.get('voice_id'), str)
                         and VOICE_ID_PATTERN.fullmatch(voice['voice_id'])), None)
        if voice_id:
            break
    if not voice_id:
        raise ValueError('No ElevenLabs voice is available for this account.')
    with _lock:
        _voices[cache_key] = (time.monotonic() + VOICE_TTL, voice_id)
    return voice_id


def synthesize(text: str, language: str) -> Optional[bytes]:
    key = current_key()
    if not key:
        return None
    with httpx.Client(timeout=20.0, follow_redirects=False) as client:
        voice_id = _choose_voice(client, key, language.lower())
        response = client.post(f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
                               headers={'xi-api-key': key},
                               json={'text': text, 'model_id': 'eleven_flash_v2_5', 'language_code': language.lower()})
        response.raise_for_status()
        if not response.content:
            raise ValueError('ElevenLabs returned empty audio.')
        return response.content


def transcribe(audio: bytes, language: str, content_type: str) -> Optional[str]:
    """Transcribe one short recording without storing the audio on disk."""
    key = current_key()
    if not key:
        return None
    extensions = {'audio/webm': 'webm', 'audio/mp4': 'm4a', 'audio/ogg': 'ogg',
                  'audio/mpeg': 'mp3', 'audio/wav': 'wav', 'audio/x-wav': 'wav'}
    extension = extensions.get(content_type)
    if extension is None:
        raise ValueError('Unsupported audio format.')
    with httpx.Client(timeout=45.0, follow_redirects=False) as client:
        response = client.post('https://api.elevenlabs.io/v1/speech-to-text', headers={'xi-api-key': key},
                               data={'model_id': 'scribe_v2', 'language_code': language.lower(),
                                     'tag_audio_events': 'false', 'timestamps_granularity': 'none'},
                               files={'file': (f'recording.{extension}', audio, content_type)})
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get('text'), str):
            raise ValueError('ElevenLabs returned an invalid transcript.')
        return body['text'].strip()
