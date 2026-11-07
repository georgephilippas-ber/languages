import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from playwright.sync_api import expect


@pytest.fixture
def book_server(tmp_path):
    # Each test starts a server with a fresh, isolated data directory.
    root = Path(__file__).resolve().parents[2]
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    env = dict(os.environ, LANGUAGES_DATA=str(tmp_path / 'isolated-data'))
    process = subprocess.Popen([sys.executable, str(root / 'bin/launcher.py'), '--port', str(port), '--no-browser'], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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
        yield url
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
        process.stdout.close()


def open_books(page, url):
    page.goto(url + '/')
    page.get_by_role('button', name='Exercises menu').click()
    page.get_by_role('menuitem', name='Books', exact=True).click()
    expect(page.get_by_role('heading', name='Books', exact=True)).to_be_visible()


def test_manual_library_status_category_and_persistence(page, book_server):
    open_books(page, book_server)
    categories = page.get_by_role('region', name='Book categories')
    for name in ('Financial', 'Legal', 'Engineering', 'Economics', 'Self-improvement'):
        expect(categories.get_by_role('button', name=re.compile('^' + name))).to_be_visible()
    page.get_by_role('button', name='Add manually').click()
    dialog = page.get_by_role('dialog', name='Add to your books')
    dialog.get_by_label('Title', exact=True).fill('The Engineer')
    dialog.get_by_label('Author').fill('A Writer')
    dialog.get_by_label('Language').fill('Greek')
    dialog.get_by_label('Category').select_option('engineering')
    dialog.get_by_label('Completion (%)').fill('42')
    dialog.get_by_label('My rating').select_option('8')
    dialog.get_by_role('button', name='Save book').click()
    current = page.get_by_role('region', name='Current books')
    expect(current.get_by_role('heading', name='The Engineer')).to_be_visible()
    expect(current.get_by_text('Greek · Engineering')).to_be_visible()
    expect(current.get_by_text('My rating: 8/10')).to_be_visible()
    expect(current.get_by_role('progressbar')).to_have_attribute('aria-valuenow', '42')
    current.get_by_role('button', name='Mark done').click()
    done = page.get_by_role('region', name='Done books')
    expect(done.get_by_role('heading', name='The Engineer')).to_be_visible()
    expect(done.get_by_role('progressbar')).to_have_attribute('aria-valuenow', '42')
    page.reload()
    expect(done.get_by_role('heading', name='The Engineer')).to_be_visible()
    categories.get_by_role('button', name=re.compile('^Non-fiction')).click()
    expect(done.get_by_role('heading', name='The Engineer')).to_be_visible()
    categories.get_by_role('button', name=re.compile('^Legal')).click()
    expect(done.get_by_role('heading', name='The Engineer')).to_have_count(0)
    categories.get_by_role('button', name=re.compile('^All')).click()
    done.get_by_role('button', name='Edit The Engineer').click()
    editor = page.get_by_role('dialog', name='Edit book')
    editor.get_by_label('Completion (%)').fill('80')
    editor.get_by_label('My rating').select_option('7')
    editor.get_by_role('button', name='Save book').click()
    expect(done.get_by_role('progressbar')).to_have_attribute('aria-valuenow', '80')
    page.reload()
    expect(done.get_by_text('My rating: 7/10')).to_be_visible()
    done.get_by_role('button', name='Delete The Engineer').click()
    page.get_by_role('dialog', name='Remove book?').get_by_role('button', name='Remove').click()
    expect(done.get_by_role('heading', name='The Engineer')).to_have_count(0)


def test_lookup_and_category_recommendation(page, book_server):
    page.set_viewport_size({'width': 390, 'height': 844})
    page.route('**/api/books/search?*', lambda route: route.fulfill(json=[{'title':'Crime and punishment', 'author':'Dostoevsky', 'isbn':'9780140449136', 'year':2003}]))
    calls = []
    page.route('**/api/books/recommend', lambda route: (calls.append(route.request.post_data_json), route.fulfill(json={'title':'Deep Work', 'author':'Cal Newport', 'language':'English', 'reason':'Useful for focused work.'})))
    open_books(page, book_server)
    page.get_by_label('Title or ISBN').fill('9780140449136')
    page.get_by_role('button', name='Search', exact=True).click()
    results = page.get_by_label('Search results')
    expect(results.get_by_text('Crime and punishment')).to_be_visible()
    results.get_by_role('button', name='Add', exact=True).click()
    editor = page.get_by_role('dialog', name='Add to your books')
    expect(editor.get_by_label('ISBN')).to_have_value('9780140449136')
    editor.get_by_label('Category').select_option('fiction')
    editor.get_by_role('button', name='Save book').click()
    expect(page.get_by_role('region', name='Current books').get_by_text('Crime and punishment')).to_be_visible()
    page.get_by_role('region', name='Book categories').get_by_role('button', name=re.compile('^Self-improvement')).click()
    page.get_by_label('Recommendation language').select_option('English')
    page.get_by_role('button', name='Suggest a book').click()
    expect(page.get_by_text('Deep Work')).to_be_visible()
    assert calls[0] == {'category':'self-improvement','language':'English'}
    page.get_by_role('button', name='Add suggestion').click()
    expect(page.get_by_role('dialog', name='Add to your books').get_by_label('Title', exact=True)).to_have_value('Deep Work')


def test_new_subject_is_persistent_even_when_empty(page, book_server):
    open_books(page, book_server)
    page.get_by_role('button', name='New subject').click()
    page.get_by_label('New subject name').fill('Cognitive Science')
    page.get_by_role('button', name='Add subject').click()
    category = page.get_by_role('region', name='Book categories').get_by_role('button', name=re.compile('^Cognitive Science'))
    expect(category).to_have_attribute('aria-pressed', 'true')
    page.reload()
    expect(category).to_be_visible()
    page.get_by_role('button', name='Add manually').click()
    expect(page.get_by_label('Category').locator('option[value="cognitive-science"]')).to_have_count(1)


def test_external_api_reference(page, book_server):
    page.goto(book_server + '/')
    page.get_by_role('button', name=re.compile('^Languages menu')).click()
    page.get_by_role('menuitem', name='External APIs').click()
    dialog = page.get_by_role('dialog', name='External APIs and services')
    for service in ('OpenAI', 'ElevenLabs', 'Open Library', 'ngrok'):
        expect(dialog.get_by_role('link', name=service, exact=True)).to_be_visible()
    dialog.get_by_role('button', name='Close').click()
    expect(dialog).not_to_be_visible()


def test_library_is_shared_across_browser_contexts(page, book_server):
    open_books(page, book_server)
    page.get_by_role('button', name='Add manually').click()
    editor = page.get_by_role('dialog', name='Add to your books')
    editor.get_by_label('Title', exact=True).fill('A shared book')
    editor.get_by_role('button', name='Save book').click()
    expect(page.get_by_role('heading', name='A shared book')).to_be_visible()
    context = page.context.browser.new_context()
    other = context.new_page()
    other.route('**/api/models', lambda route: route.fulfill(json={'default':'test-model','models':['test-model']}))
    other.goto(book_server + '/books')
    expect(other.get_by_role('heading', name='A shared book')).to_be_visible()
    context.close()
