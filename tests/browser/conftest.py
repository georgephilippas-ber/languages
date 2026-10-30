import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest

from src.domain import DATA_ROOT

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def server():
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    process = subprocess.Popen([sys.executable, str(ROOT / 'bin/launcher.py'), '--port', str(port), '--no-browser'],
                               cwd=ROOT, env=dict(os.environ, LANGUAGES_DATA=DATA_ROOT),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(150):
            if process.poll() is not None:
                pytest.fail(process.stdout.read())
            try:
                with urlopen(url + '/api/health', timeout=.3):
                    break
            except OSError:
                time.sleep(.1)
        else:
            pytest.fail('Test server did not start')
        yield url, process
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
        process.stdout.close()


@pytest.fixture(params=['chromium', 'firefox'])
def browser(request):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        options = {'firefox_user_prefs': {'dom.allow_scripts_to_close_windows': True}} if request.param == 'firefox' else {}
        instance = getattr(playwright, request.param).launch(**options)
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(reduced_motion='reduce')
    page = context.new_page()
    page.route('**/api/models', lambda route: route.fulfill(json={'default': 'test-model', 'models': ['test-model']}))
    yield page
    context.close()
