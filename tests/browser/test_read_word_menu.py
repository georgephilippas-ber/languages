import re
import pytest
from playwright.sync_api import expect

ARTICLE = {'topic': 'physics', 'title': 'Ein neuer Rekord', 'publication': 'Test Publisher',
           'url': 'https://example.com/article', 'publishedAt': '2026-10-29T12:00:00+00:00',
           'retrievedAt': '2026-10-30T07:00:00+00:00',
           'summary': 'Forscher melden einen Rekord.', 'words': ['Rekord']}


def mock_article(page):
    page.route('**/api/read', lambda route: route.fulfill(json=ARTICLE))


def test_right_click_word_adds_to_chosen_category_then_highlights_green(page, server):
    saved = []
    mock_article(page)
    page.route('**/api/entries/define', lambda route: route.fulfill(json={
        'term': 'der Rekord', 'markdown': '## der Rekord\n\n**Definition:** Best result.\n', 'gloss': 'record'}))
    def save(route):
        saved.append(route.request.post_data_json)
        route.fulfill(json={'saved': [{'term': 'der Rekord', 'fileName': 'german-financial-1.md', 'termsInFile': 1}],
                            'fileName': 'german-financial-1.md', 'termsInFile': 1, 'fileFull': False})
    page.route('**/api/entries/save', save)
    page.goto(server[0] + '/read')
    page.get_by_role('button', name='physics', exact=True).click()
    page.get_by_role('button', name='Retrieve', exact=False).click()
    word = page.get_by_title('Rekord · physics vocabulary at this level').last
    expect(word).to_be_visible()
    word.click(button='right')
    menu = page.get_by_role('menu', name='Options for Rekord')
    expect(menu).to_be_visible()
    expect(menu.get_by_role('menuitem', name='Phrasal Verbs')).to_have_count(0)
    menu.get_by_role('menuitem', name='Financial').click()
    assert page.url.endswith('/read')
    expect(page.get_by_title('Queued for Add')).to_have_count(2)
    assert not saved
    page.locator('header').get_by_role('link', name='Add').click()
    expect(page.get_by_label('Category for Rekord')).to_have_value('financial')
    page.get_by_role('button', name='Add 1 entry').click()
    expect(page.get_by_role('button', name='Back to article')).to_be_visible()
    assert saved[0]['language'] == 'DE' and saved[0]['category'] == 'financial'
    page.get_by_role('button', name='Back to article').click()
    added = page.get_by_title('Added to vocabulary')
    expect(added).to_have_count(2)
    expect(added.last).to_have_text('Rekord.')
    expect(added.last).to_have_class(re.compile('text-good'))
    page.reload()
    expect(page.get_by_title('Added to vocabulary')).to_have_count(2)


@pytest.mark.parametrize('code,language', [('EN', 'English'), ('FR', 'French')])
def test_context_menu_uses_current_language_and_escape(page, server, code, language):
    mock_article(page)
    page.goto(server[0] + '/')
    page.get_by_role('button', name=code, exact=True).click()
    page.goto(server[0] + '/read')
    page.get_by_role('button', name='Retrieve', exact=False).click()
    page.get_by_text('Forscher', exact=True).click(button='right')
    menu = page.get_by_role('menu', name='Options for Forscher')
    expect(menu).to_be_visible()
    expect(menu.get_by_role('menuitem', name='Phrasal Verbs')).to_have_count(1 if code == 'EN' else 0)
    page.keyboard.press('Escape')
    expect(menu).to_have_count(0)
    page.get_by_text('Forscher', exact=True).click(button='right')
    menu.get_by_role('menuitem', name='Legal').click()
    assert page.url.endswith('/read')
    expect(page.get_by_title('Queued for Add')).to_have_count(1)
    draft = page.evaluate("JSON.parse(localStorage.getItem('languages.drafts'))[0]")
    assert draft['language'] == code and draft['category'] == 'legal'


def test_highlighted_words_added_together_are_marked_after_save(page, server):
    mock_article(page)
    page.route('**/api/entries/define', lambda route: route.fulfill(json={
        'term': 'der Rekord', 'markdown': '## der Rekord\n\n**Definition:** Best result.\n', 'gloss': 'record'}))
    page.route('**/api/entries/save', lambda route: route.fulfill(json={
        'saved': [{'term': 'der Rekord', 'fileName': 'german-1.md', 'termsInFile': 13}],
        'fileName': 'german-1.md', 'termsInFile': 13, 'fileFull': False}))
    page.goto(server[0] + '/read')
    page.get_by_role('button', name='Retrieve', exact=False).click()
    page.get_by_role('button', name='Words to Add').click()
    assert page.url.endswith('/read')
    expect(page.get_by_title('Queued for Add')).to_have_count(2)
    page.locator('header').get_by_role('link', name='Add').click()
    page.get_by_role('button', name='Add 1 entry').click()
    page.get_by_role('button', name='Back to article').click()
    expect(page.get_by_title('Added to vocabulary')).to_have_count(2)


def test_different_categories_are_saved_separately(page, server):
    mock_article(page)
    def define(route):
        term = route.request.post_data_json['term']
        route.fulfill(json={'term': term, 'markdown': f'## {term}\n\n**Definition:** A word.\n', 'gloss': 'word'})
    saved = []
    def save(route):
        data = route.request.post_data_json
        saved.append(data)
        term = data['entries'][0].splitlines()[0][3:]
        name = f"german-{data['category']}-1.md"
        route.fulfill(json={'saved': [{'term': term, 'fileName': name, 'termsInFile': 1}], 'fileName': name, 'termsInFile': 1, 'fileFull': False})
    page.route('**/api/entries/define', define)
    page.route('**/api/entries/save', save)
    page.goto(server[0] + '/read')
    page.get_by_role('button', name='Retrieve', exact=False).click()
    page.get_by_text('Forscher', exact=True).click(button='right')
    page.get_by_role('menuitem', name='Legal').click()
    page.get_by_title('Rekord · physics vocabulary at this level').last.click(button='right')
    page.get_by_role('menuitem', name='Financial').click()
    expect(page.get_by_title('Queued for Add')).to_have_count(3)
    page.locator('header').get_by_role('link', name='Add').click()
    page.get_by_role('button', name='Add 2 entries').click()
    expect(page.get_by_role('button', name='Back to article')).to_be_visible()
    assert [item['category'] for item in saved] == ['legal', 'financial']
    page.get_by_role('button', name='Back to article').click()
    expect(page.get_by_title('Added to vocabulary')).to_have_count(3)
