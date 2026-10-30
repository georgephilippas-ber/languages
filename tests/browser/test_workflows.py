import json
import re
from pathlib import Path

import pytest

from src.domain import DATA_ROOT

pytestmark = pytest.mark.browser

ENTRY = '## die Krähe\n\n**CEFR:** roughly **B1**.\n\n**Definition:** A black bird.\n\n**Grammar:** Feminine noun.\n\n**English:** crow · **French:** la corneille'


def test_add_draft_reload_save_and_persist(page, server):
    from playwright.sync_api import expect
    url, _ = server
    page.route('**/api/entries/define', lambda route: route.fulfill(json={'term': 'die Krähe', 'markdown': ENTRY, 'gloss': 'crow'}))
    page.goto(url + '/add')
    words = page.get_by_role('textbox', name='German vocabulary, one per line')
    words.fill('die Krähe')
    page.get_by_role('button', name=re.compile(r'^Write entries')).click()
    expect(page.get_by_role('button', name='Add 1 entry', exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_role('button', name='Add 1 entry', exact=True)).to_be_visible()
    with page.expect_response(lambda response: response.url.endswith('/api/entries/save') and response.status == 200):
        page.get_by_role('button', name='Add 1 entry', exact=True).click()
    expect(page.get_by_text('Added', exact=False).first).to_be_visible()
    page.reload()
    expect(page.get_by_role('button', name='Add 1 entry', exact=True)).to_have_count(0)
    files = list((Path(DATA_ROOT)/'vocabulary/german').glob('german-*.md'))
    assert sum(file.read_text().count('## die Krähe') for file in files) == 1


def test_exercise_resume_and_language_switch(page, server):
    from playwright.sync_api import expect
    url, _ = server
    calls = []
    def generate(route):
        calls.append(route.request.post_data_json)
        route.fulfill(json={'source': 'german-1.md', 'questions': [
            {'term': f'term {i}', 'question': f'Satz {i} mit _____.', 'choices': ['alpha', 'beta', 'gamma', 'delta'],
             'correctChoice': 0, 'completeSentence': f'Satz {i} mit alpha.', 'englishTranslation': 'A sentence.',
             'choicesTranslations': ['a', 'b', 'c', 'd']} for i in (1, 2)]})
    page.route('**/api/quiz', generate)
    page.goto(url + '/quiz')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('button', name='A alpha', exact=True).click()
    page.get_by_role('button', name='Next', exact=False).click()
    expect(page.get_by_text('Satz 2 mit', exact=False)).to_be_visible()
    page.reload()
    page.get_by_role('button', name='Resume', exact=True).click()
    expect(page.get_by_text('Satz 2 mit', exact=False)).to_be_visible()
    assert len(calls) == 1
    page.get_by_role('button', name='FR', exact=True).click()
    page.goto(url + '/quiz')
    expect(page.get_by_role('button', name='Resume', exact=True)).to_have_count(0)


def test_read_shows_source_date_and_survives_reload(page, server):
    from playwright.sync_api import expect
    url, _ = server
    page.route('**/api/read', lambda route: route.fulfill(json={
        'topic': 'physics', 'title': 'A retrieved physics article', 'publication': 'Test Publisher',
        'url': 'https://example.com/article', 'publishedAt': '2026-10-29T12:00:00+00:00',
        'retrievedAt': '2026-10-30T07:00:00+00:00', 'summary': 'Forscher melden einen Rekord.', 'words': ['Rekord']}))
    page.goto(url + '/read')
    page.get_by_role('button', name='physics', exact=True).click()
    page.get_by_role('button', name='Retrieve', exact=False).click()
    expect(page.get_by_role('link', name='Test Publisher')).to_have_attribute('href', 'https://example.com/article')
    expect(page.locator('time')).to_have_attribute('datetime', '2026-10-29T12:00:00+00:00')
    page.reload()
    expect(page.get_by_role('heading', name='A retrieved physics article')).to_be_visible()


def test_exit_cancel_then_closes_tab_and_stops_worker(page, server):
    from playwright.sync_api import expect
    url, process = server
    page.goto(url)
    page.get_by_role('button', name='Languages menu', exact=True).click()
    page.get_by_role('menuitem', name='Exit Languages', exact=True).click()
    page.get_by_role('button', name='Cancel', exact=True).click()
    assert process.poll() is None
    page.get_by_role('button', name='Languages menu', exact=True).click()
    page.get_by_role('menuitem', name='Exit Languages', exact=True).click()
    # A script-created tab can close in Chromium; configured Firefox also permits ordinary tabs.
    if page.context.browser.browser_type.name == 'chromium':
        page.evaluate('window.close = () => {}')
        page.get_by_role('button', name='Quit', exact=True).click()
        expect(page.get_by_role('heading', name='Languages has quit')).to_be_visible()
    else:
        with page.expect_event('close'):
            page.get_by_role('button', name='Quit', exact=True).click()
    assert process.wait(timeout=10) == 0
