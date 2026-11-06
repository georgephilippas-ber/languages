"""Opt-in checks for a built macOS app, using disposable data only."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen

import pytest
import httpx

pytestmark = [pytest.mark.packaged, pytest.mark.skipif(sys.platform != 'darwin', reason='macOS bundle')]


def wait_ready(url, process, root):
    for _ in range(200):
        if process.poll() is not None:
            pytest.fail(f'App launcher exited early: {process.returncode}')
        try:
            with urlopen(url + '/api/health', timeout=.5) as response:
                health = json.load(response)
            assert health['application'] == 'languages' and health['dataRoot'] == str(root.resolve())
            return
        except OSError:
            time.sleep(.1)
    pytest.fail('Packaged app did not start')


def exit_backend(url):
    with urlopen(url + '/api/lifecycle') as response:
        token = json.load(response)['exitToken']
    with urlopen(Request(url + '/api/exit', method='POST', headers={'X-Languages-Exit': token})) as response:
        assert json.load(response)['status'] == 'quitting'


@pytest.fixture
def app(request, tmp_path):
    built = Path(request.config.getoption('--app-path')).resolve()
    assert (built / 'Contents/MacOS/Languages').is_file(), 'Build scripts/build.sh first'
    moved = tmp_path / 'Relocated app' / 'Languages.app'
    moved.parent.mkdir()
    shutil.copytree(built, moved, symlinks=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(moved)], check=True)
    return moved


def test_relocated_runtime_frontend_duplicate_launch_and_exit(app, tmp_path):
    root = tmp_path / 'data'
    worker = app / 'Contents/Resources/runtime/languages/languages'
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    env = dict(os.environ, LANGUAGES_DATA=str(root))
    process = subprocess.Popen([str(worker), '--port', str(port), '--no-browser'], env=env, cwd=tmp_path)
    try:
        wait_ready(url, process, root)
        for number in (1, 2):
            seed = Path(__file__).resolve().parents[2] / 'seed' / f'en-phrasal-verbs-{number}.md'
            shutil.copyfile(seed, root / 'vocabulary' / 'english' / f'english-phrasal-verbs-{number}.md')
        with urlopen(url + '/api/meta') as response:
            meta = json.load(response)
            assert meta['defaults']['level'] == 'C1'
            english = next(item for item in meta['languages'] if item['code'] == 'EN')
            assert [(item['number'], item['terms']) for item in english['files']] == [
                ('phrasal-verbs:1', 25), ('phrasal-verbs:2', 25)]
        for selection, count in (('phrasal-verbs:current', 25), ('phrasal-verbs:latest', 50),
                                 ('phrasal-verbs', 50), ('all', 50)):
            request = Request(url + '/api/flashcards', data=json.dumps({'language': 'EN', 'files': selection}).encode(),
                              headers={'Content-Type': 'application/json'}, method='POST')
            with urlopen(request) as response:
                assert len(json.load(response)['cards']) == count
        with urlopen(url + '/quiz') as response:
            assert b'assets/index-' in response.read()
        with urlopen(url + '/api/internet') as response:
            assert json.load(response)['active'] is False
        with urlopen(Request(url + '/api/internet/stop', method='POST')) as response:
            assert not json.load(response)['active']
        with urlopen(Request(url + '/api/device/start', method='POST')) as response:
            device = json.load(response)
            assert device['active'] and device['qr'].startswith('data:image/svg+xml;base64,')
            assert device['localQr'].startswith('data:image/svg+xml;base64,')
            assert device['localUrl'] == device['url'].split('/join/', 1)[0]
        with httpx.Client(trust_env=False, follow_redirects=False) as shared:
            response = shared.get(device['localUrl'])
            assert response.status_code == 200 and not shared.cookies
        with urlopen(Request(url + '/api/device/revoke', method='POST')) as response:
            assert not json.load(response)['active']
        second = subprocess.run([str(worker), '--port', str(port), '--no-browser'], env=env, cwd=tmp_path, timeout=15)
        assert second.returncode == 0 and process.poll() is None
        exit_backend(url)
        assert process.wait(timeout=15) == 0
    finally:
        if process.poll() is None:
            process.terminate(); process.wait(timeout=10)


def test_native_launch_reopen_and_backend_exit(app, tmp_path):
    with socket.socket() as connection:
        if connection.connect_ex(('127.0.0.1', 8100)) == 0:
            pytest.skip('Port 8100 belongs to a running app; close it before testing')
    root = tmp_path / 'native-data'
    process = subprocess.Popen(['open', '-n', '-W', str(app), '--env', f'LANGUAGES_DATA={root}',
                                '--env', 'LANGUAGES_NO_BROWSER=1'])
    url = 'http://127.0.0.1:8100'
    try:
        wait_ready(url, process, root)
        subprocess.run(['open', str(app)], check=True)
        wait_ready(url, process, root)
        exit_backend(url)
        assert process.wait(timeout=15) == 0
        with socket.socket() as connection:
            assert connection.connect_ex(('127.0.0.1', 8100)) != 0
    finally:
        if process.poll() is None:
            try:
                exit_backend(url)
                process.wait(timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                process.terminate(); process.wait(timeout=5)


def test_packaged_article_extractor(request, tmp_path):
    built = Path(request.config.getoption('--app-path')).resolve()
    worker = built / 'Contents/Resources/runtime/languages/languages'
    result = subprocess.run([str(worker), '--check-read'], cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert 'Article extraction is available.' in result.stdout
