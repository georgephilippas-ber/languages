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
    page.get_by_role('menuitem', name='BOOKS', exact=True).click()
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
    dialog.get_by_label('Category', exact=True).select_option('engineering')
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
    editor.get_by_label('Category', exact=True).select_option('fiction')
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
    expect(page.get_by_label('Category', exact=True).locator('option[value="cognitive-science"]')).to_have_count(1)


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


def test_book_notes_edit_preview_save_and_close(page, book_server):
    open_books(page, book_server)
    page.get_by_role('button', name='Add manually').click()
    editor = page.get_by_role('dialog', name='Add to your books')
    editor.get_by_label('Title', exact=True).fill('Notes book')
    editor.get_by_role('button', name='Save book').click()
    page.get_by_role('button', name='Notes for Notes book').click()
    notes = page.get_by_role('dialog', name='Book notes')
    text = notes.get_by_label('Markdown notes')
    text.fill('# Key ideas\n\n**Important** and $x^2$')
    preview = notes.get_by_label('Notes preview')
    expect(preview.get_by_role('heading', name='Key ideas')).to_be_visible()
    expect(preview.locator('strong')).to_have_text('Important')
    expect(preview.locator('.katex').first).to_be_visible()
    notes.get_by_role('button', name='Save notes').click()
    expect(notes.get_by_role('status')).to_have_text('Saved')
    notes.get_by_role('button', name='Close').click()
    page.reload()
    page.get_by_role('button', name='Notes for Notes book').click()
    expect(text).to_have_value('# Key ideas\n\n**Important** and $x^2$')
    text.fill('Unsaved')
    notes.get_by_role('button', name='Close').click()
    page.get_by_role('dialog', name='Discard unsaved notes?').get_by_role('button', name='Keep editing').click()
    expect(text).to_have_value('Unsaved')
    notes.get_by_role('button', name='Close').click()
    page.get_by_role('dialog', name='Discard unsaved notes?').get_by_role('button', name='Discard changes').click()
    page.get_by_role('button', name='Notes for Notes book').click()
    expect(text).to_have_value('# Key ideas\n\n**Important** and $x^2$')


def test_current_book_progress_by_percentage_and_page(page, book_server):
    page.route('**/api/books/*/page-count', lambda route: route.fulfill(json={'totalPages': 320}))
    open_books(page, book_server)
    page.get_by_role('button', name='Add manually').click()
    dialog = page.get_by_role('dialog', name='Add to your books')
    dialog.get_by_label('Title', exact=True).fill('Progress book')
    dialog.get_by_label('ISBN').fill('9780140449136')
    dialog.get_by_label('My rating').select_option('8')
    dialog.get_by_role('button', name='Save book').click()
    form = page.get_by_role('form', name='Update progress for Progress book')
    expect(form.get_by_label('Current page')).to_be_visible()
    expect(form.get_by_label('Current page')).to_be_disabled()
    expect(form.get_by_label('Completion (%)')).to_be_visible()
    expect(page.get_by_role('button', name='Update progress for Progress book')).to_have_count(0)
    form.get_by_label('Completion (%)').fill('30')
    form.get_by_role('button', name='Save', exact=True).click()
    expect(page.get_by_role('progressbar', name='Progress book completion')).to_have_attribute('aria-valuenow', '30')
    expect(form.get_by_label('Current page')).to_be_disabled()
    form.get_by_label('Last readable page').focus()
    expect(form.get_by_label('Last readable page')).to_have_attribute('placeholder', '320')
    expect(form.get_by_label('Current page')).to_be_disabled()
    form.get_by_label('Last readable page').fill('320')
    expect(form.get_by_label('Current page')).to_be_enabled()
    form.get_by_label('Current page').fill('80')
    expect(form.get_by_text('25% complete · last readable page 320')).to_be_visible()
    expect(form.get_by_label('Completion (%)')).to_have_value('25')
    form.get_by_role('button', name='Save', exact=True).click()
    expect(page.get_by_text('Page 80 · Last readable page: 320')).to_be_visible()
    expect(page.get_by_role('progressbar', name='Progress book completion')).to_have_attribute('aria-valuenow', '25')
    page.reload()
    expect(page.get_by_text('Page 80 · Last readable page: 320')).to_be_visible()
    expect(page.get_by_text('My rating: 8/10')).to_be_visible()
    form.get_by_label('Completion (%)').fill('50')
    expect(form.get_by_label('Current page')).to_have_value('')
    form.get_by_role('button', name='Save', exact=True).click()
    expect(page.get_by_role('progressbar', name='Progress book completion')).to_have_attribute('aria-valuenow', '50')
    page.reload()
    expect(form.get_by_label('Current page')).to_have_value('')
    expect(form.get_by_label('Completion (%)')).to_have_value('50')


def test_notes_toolbar_headings_linter_and_undo(page, book_server):
    page.set_viewport_size({'width': 600, 'height': 850})
    open_books(page, book_server)
    page.get_by_role('button', name='Add manually').click()
    editor = page.get_by_role('dialog', name='Add to your books')
    editor.get_by_label('Title', exact=True).fill('Editing book')
    editor.get_by_role('button', name='Save book').click()
    page.get_by_role('button', name='Notes for Editing book').click()
    notes = page.get_by_role('dialog', name='Book notes')
    text = notes.get_by_label('Markdown notes')
    text.fill('Concept')
    text.press('Home')
    notes.get_by_role('button', name='Heading 6 (Ctrl+6)').click()
    expect(text).to_have_value('###### Concept')
    notes.get_by_role('button', name='Heading 4 (Ctrl+4)').click()
    expect(text).to_have_value('#### Concept')
    expect(notes.get_by_role('button', name='Heading 5 (Ctrl+5)')).to_be_visible()
    notes.get_by_text('Math & symbols').click()
    expect(notes.get_by_role('button', name='Fraction')).to_be_visible()
    text.fill('#Title\n\nFormula: $x^2$\n')
    notes.get_by_role('button', name='Check Markdown').click()
    results = notes.get_by_role('region', name='Markdown check results')
    expect(results).to_contain_text('Fixed')
    expect(text).to_have_value('# Title\n\nFormula: $x^2$\n')
    notes.get_by_role('button', name='Undo fixes').click()
    expect(text).to_have_value('#Title\n\nFormula: $x^2$\n')


def test_book_covers_and_fallback_icon(page, book_server):
    import base64
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRk0AAAAASUVORK5CYII=')
    page.route('**/api/books/*/cover?*', lambda route: route.fulfill(status=200, content_type='image/png', body=png))
    open_books(page, book_server)
    page.get_by_role('button', name='Add manually').click()
    dialog = page.get_by_role('dialog', name='Add to your books')
    dialog.get_by_label('Title', exact=True).fill('Covered book')
    dialog.get_by_label('ISBN').fill('9780140449136')
    dialog.get_by_role('button', name='Save book').click()
    card = page.locator('article').filter(has=page.get_by_role('heading', name='Covered book'))
    expect(card.locator('img')).to_be_visible()
    page.get_by_role('button', name='Add manually').click()
    dialog = page.get_by_role('dialog', name='Add to your books')
    dialog.get_by_label('Title', exact=True).fill('No ISBN book')
    dialog.get_by_role('button', name='Save book').click()
    fallback = page.locator('article').filter(has=page.get_by_role('heading', name='No ISBN book'))
    expect(fallback.locator('img')).to_have_count(0)
    expect(fallback.locator('svg').first).to_be_visible()


def test_to_read_manual_categories_and_start_reading(page, book_server):
    open_books(page, book_server)
    section = page.get_by_role('region', name='To Read list')
    for name in ('Work', 'Education', 'Personal Development', 'Literature'):
        expect(section.get_by_role('region', name=f'{name} To Read')).to_be_visible()
    section.get_by_role('button', name='Add a book').click()
    editor = page.get_by_role('dialog', name='Add to To Read')
    editor.get_by_label('Title', exact=True).fill('A Future Book')
    editor.get_by_label('Author').fill('An Author')
    editor.get_by_label('Personal category').select_option('literature')
    editor.get_by_role('button', name='Save to list').click()
    literature = section.get_by_role('region', name='Literature To Read')
    expect(literature.get_by_text('A Future Book')).to_be_visible()
    page.reload()
    expect(literature.get_by_text('A Future Book')).to_be_visible()
    literature.get_by_role('button', name='Edit A Future Book in To Read').click()
    editor = page.get_by_role('dialog', name='Edit To Read book')
    editor.get_by_label('Personal category').select_option('education')
    editor.get_by_role('button', name='Save to list').click()
    education = section.get_by_role('region', name='Education To Read')
    expect(education.get_by_text('A Future Book')).to_be_visible()
    education.get_by_role('button', name='Start reading').click()
    expect(education.get_by_text('A Future Book')).to_have_count(0)
    expect(page.get_by_role('region', name='Current books').get_by_role('heading', name='A Future Book')).to_be_visible()
    expect(page.get_by_role('region', name='Book categories').get_by_role('button', name=re.compile('^Literature'))).to_be_visible()


def test_add_recommendation_to_read_waits_for_explicit_refresh(page, book_server):
    calls = []
    def recommend(route):
        calls.append(route.request.post_data_json)
        book = {'title':'Deep Work', 'author':'Cal Newport', 'language':'English', 'reason':'Useful.'} if len(calls) == 1 else {'title':'A Different Book', 'author':'New Writer', 'language':'English', 'reason':'Another choice.'}
        route.fulfill(json=book)
    page.route('**/api/books/recommend', recommend)
    open_books(page, book_server)
    page.get_by_label('Recommendation language').select_option('English')
    page.get_by_role('button', name='Suggest a book').click()
    expect(page.get_by_text('Deep Work')).to_be_visible()
    page.get_by_label('To Read category').select_option('work')
    page.get_by_role('button', name='Add to To Read', exact=True).click()
    expect(page.get_by_role('region', name='Work To Read').get_by_text('Deep Work')).to_be_visible()
    expect(page.get_by_role('status').filter(has_text='Added')).to_be_visible()
    assert len(calls) == 1
    page.get_by_role('button', name='Suggest a book').click()
    expect(page.get_by_text('A Different Book')).to_be_visible()
    assert len(calls) == 2 and calls[1]['category'] == calls[0]['category'] and calls[1]['language'] == 'English'
    assert calls[1]['exclude'] == [{'title':'Deep Work','author':'Cal Newport'}]
    page.reload()
    expect(page.get_by_role('region', name='Work To Read').get_by_text('Deep Work')).to_be_visible()


def test_current_and_done_group_books_by_personal_category(page, book_server):
    open_books(page, book_server)
    current = page.get_by_role('region', name='Current books')
    done = page.get_by_role('region', name='Done books')
    for name in ('Work', 'Education', 'Personal Development', 'Literature'):
        expect(current.get_by_role('region', name=f'{name} Current')).to_be_visible()
        expect(done.get_by_role('region', name=f'{name} Done')).to_be_visible()
    page.get_by_role('button', name='Add manually').click()
    editor = page.get_by_role('dialog', name='Add to your books')
    editor.get_by_label('Title', exact=True).fill('A Work Book')
    editor.get_by_label('Category', exact=True).select_option('legal')
    editor.get_by_label('Personal category').select_option('work')
    editor.get_by_role('button', name='Save book').click()
    group = current.get_by_role('region', name='Work Current')
    expect(group.get_by_role('heading', name='A Work Book')).to_be_visible()
    expect(group.get_by_text('Legal')).to_be_visible()
    group.get_by_role('button', name='Mark done').click()
    group = done.get_by_role('region', name='Work Done')
    expect(group.get_by_role('heading', name='A Work Book')).to_be_visible()
    group.get_by_role('button', name='Edit A Work Book').click()
    editor = page.get_by_role('dialog', name='Edit book')
    expect(editor.get_by_label('Category', exact=True)).to_have_value('legal')
    editor.get_by_label('Personal category').select_option('education')
    editor.get_by_role('button', name='Save book').click()
    group = done.get_by_role('region', name='Education Done')
    expect(group.get_by_role('heading', name='A Work Book')).to_be_visible()
    page.reload()
    expect(group.get_by_role('heading', name='A Work Book')).to_be_visible()


def test_books_navigation_has_only_back_to_languages(page, book_server):
    for width in (390, 1440):
        page.set_viewport_size({'width': width, 'height': 850})
        open_books(page, book_server)
        header = page.locator('header')
        back = header.get_by_role('link', name='Back to Languages')
        expect(back).to_be_visible()
        expect(header.locator('a, button')).to_have_count(1)
        page.reload()
        expect(back).to_be_visible()
        back.click()
        expect(page).to_have_url(re.compile(r'/$'))
        expect(header.get_by_role('button', name='Exercises menu')).to_be_visible()


def test_book_manual_last_readable_page_and_later_page_progress(page, book_server):
    open_books(page, book_server)
    page.get_by_role('button', name='Add manually').click()
    dialog = page.get_by_role('dialog', name='Add to your books')
    dialog.get_by_label('Title', exact=True).fill('Manual page book')
    dialog.get_by_role('button', name='Save book').click()
    form = page.get_by_role('form', name='Update progress for Manual page book')
    expect(form.get_by_label('Current page')).to_be_disabled()
    form.get_by_label('Last readable page').fill('400')
    expect(form.get_by_label('Current page')).to_be_enabled()
    form.get_by_role('button', name='Save', exact=True).click()
    expect(page.get_by_text('Last readable page: 400')).to_be_visible()
    page.reload()
    form.get_by_label('Current page').fill('100')
    expect(form.get_by_text('25% complete · last readable page 400')).to_be_visible()
    form.get_by_role('button', name='Save', exact=True).click()
    expect(page.get_by_role('progressbar', name='Manual page book completion')).to_have_attribute('aria-valuenow', '25')
    page.reload()
    expect(page.get_by_text('Page 100 · Last readable page: 400')).to_be_visible()


def test_reading_section_order_and_five_book_limit(page, book_server):
    data = {'author':'Writer', 'language':'English', 'progress':0, 'status':'current', 'category':'other'}
    for i in range(5):
        assert page.request.post(book_server + '/api/books', data={**data, 'title':f'Current {i}'}).status == 201
    assert page.request.post(book_server + '/api/books/to-read', data={'title':'Waiting', 'author':'Writer', 'language':'English', 'category':'work'}).status == 201
    open_books(page, book_server)
    expect(page.get_by_role('region', name='Current books')).to_be_visible()
    assert page.locator('section[aria-label="Current books"], section[aria-label="To Read list"], section[aria-label="Done books"]').evaluate_all('(sections) => sections.map((e) => e.getAttribute("aria-label"))') == ['Current books', 'To Read list', 'Done books']
    current = page.get_by_role('region', name='Current books')
    expect(current.get_by_role('heading', name='Current 5 / 5')).to_be_visible()
    waiting = page.get_by_role('region', name='Work To Read')
    expect(waiting.get_by_role('button', name='Start reading')).to_be_enabled()
    waiting.get_by_role('button', name='Start reading').click()
    expect(page.get_by_role('region', name='To Read list').get_by_role('alert')).to_contain_text('Move at least 1')
    expect(waiting.get_by_text('Waiting')).to_be_visible()
    page.get_by_role('button', name='Add manually').click()
    editor = page.get_by_role('dialog', name='Add to your books')
    expect(editor.get_by_role('button', name='Save book')).to_be_disabled()
    expect(editor.get_by_role('status')).to_contain_text('Current is full')
    editor.get_by_role('button', name='Cancel').click()
    current.locator('article').filter(has=page.get_by_role('heading', name='Current 0', exact=True)).get_by_role('button', name='Mark done').click()
    expect(waiting.get_by_role('button', name='Start reading')).to_be_enabled()
    waiting.get_by_role('button', name='Start reading').click()
    expect(current.get_by_role('heading', name='Waiting', exact=True)).to_be_visible()
    expect(current.get_by_role('heading', name='Current 5 / 5')).to_be_visible()


def test_suggestion_box_can_close_and_reopen(page, book_server):
    open_books(page, book_server)
    suggestions = page.get_by_role('region', name='Book recommendation')
    expect(suggestions).to_be_visible()
    suggestions.get_by_role('button', name='Close suggestions').click()
    expect(suggestions).to_have_count(0)
    page.get_by_role('button', name='Show book suggestions').click()
    expect(suggestions).to_be_visible()


def test_book_form_validation_and_page_boundary(page, book_server):
    open_books(page, book_server)
    page.get_by_role('button', name='Add manually').click()
    editor = page.get_by_role('dialog', name='Add to your books')
    editor.get_by_label('Title', exact=True).fill('   ')
    editor.get_by_role('button', name='Save book').click()
    expect(editor.get_by_role('alert')).to_have_text('Enter a title.')
    editor.get_by_label('Title', exact=True).fill('Validation book')
    editor.get_by_label('ISBN').fill('9780306406158')
    editor.get_by_role('button', name='Save book').click()
    expect(editor.get_by_role('alert')).to_contain_text('valid ISBN')
    editor.get_by_label('ISBN').fill('')
    editor.get_by_role('button', name='Save book').click()
    form = page.get_by_role('form', name='Update progress for Validation book')
    form.get_by_label('Last readable page').fill('200')
    form.get_by_label('Current page').fill('201')
    expect(form.get_by_role('alert')).to_contain_text('cannot exceed the last readable page')
    form.get_by_label('Current page').fill('200')
    expect(form.get_by_role('alert')).to_have_count(0)
    form.get_by_role('button', name='Save', exact=True).click()
    expect(page.get_by_role('progressbar', name='Validation book completion')).to_have_attribute('aria-valuenow', '100')


def test_start_reading_uses_live_count_if_another_device_freed_a_slot(page, book_server):
    data = {'author':'Writer', 'language':'English', 'progress':0, 'status':'current', 'category':'other'}
    for i in range(4):
        assert page.request.post(book_server + '/api/books', data={**data, 'title':f'Actual {i}'}).status == 201
    assert page.request.post(book_server + '/api/books/to-read', data={'title':'Ready', 'author':'Writer', 'language':'English', 'category':'work'}).status == 201
    books = page.request.get(book_server + '/api/books').json()
    ghost = {**books[0], 'id':'stale-book', 'title':'Stale book'}
    first = [True]
    def stale_once(route):
        if route.request.method == 'GET' and first[0]:
            first[0] = False
            route.fulfill(json=[*books, ghost])
        else:
            route.continue_()
    page.route('**/api/books', stale_once)
    open_books(page, book_server)
    current = page.get_by_role('region', name='Current books')
    expect(current.get_by_role('heading', name='Current 5 / 5')).to_be_visible()
    page.get_by_role('region', name='Work To Read').get_by_role('button', name='Start reading').click()
    expect(current.get_by_role('heading', name='Ready', exact=True)).to_be_visible()
    expect(current.get_by_role('heading', name='Stale book', exact=True)).to_have_count(0)
    expect(current.get_by_role('heading', name='Current 5 / 5')).to_be_visible()
