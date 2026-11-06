import re
from playwright.sync_api import expect
from test_use_dictation import MOCK_RECORDER


def test_switch_language_on_add_preserves_unsent_text_and_queued_entries(page, server):
    calls = []
    def define(route):
        payload = route.request.post_data_json
        calls.append(payload)
        word = payload['term']
        route.fulfill(json={'term': word, 'markdown': f'## {word}\n\n**Definition:** A word.', 'gloss': 'word'})
    page.route('**/api/entries/define', define)
    page.goto(server[0] + '/add')
    header = page.locator('header')
    de = page.get_by_role('textbox', name='German vocabulary, one per line')
    de.fill('das Wort')
    header.get_by_role('button', name='FR', exact=True).click()
    expect(page).to_have_url(re.compile('/add$'))
    fr = page.get_by_role('textbox', name='French vocabulary, one per line')
    expect(fr).to_have_value('')
    fr.fill('le mot')
    page.get_by_role('button', name='Write entries').click()
    expect(page.get_by_role('button', name='Add 1 entry')).to_be_visible()
    assert calls[0]['language'] == 'FR' and calls[0]['term'] == 'le mot'
    header.get_by_role('button', name='DE', exact=True).click()
    expect(de).to_have_value('das Wort')
    expect(page.get_by_role('button', name='Add 1 entry')).to_have_count(0)
    header.get_by_role('button', name='FR', exact=True).click()
    expect(page.get_by_role('button', name='Add 1 entry')).to_be_visible()
    drafts = page.evaluate("JSON.parse(localStorage.getItem('languages.drafts'))")
    assert len(drafts) == 1 and drafts[0]['language'] == 'FR'


def test_switch_language_stops_active_dictation_and_can_restart(page, server):
    page.add_init_script(MOCK_RECORDER)
    calls = []
    page.route('**/api/transcribe?*', lambda route: (calls.append(route.request.url), route.fulfill(json={'text': 'bonjour'})))
    page.goto(server[0] + '/add')
    page.get_by_role('button', name='Speak a word or sentence').click()
    expect(page.get_by_role('button', name='Stop and transcribe')).to_be_visible()
    page.locator('header').get_by_role('button', name='FR', exact=True).click()
    expect(page.get_by_role('button', name='Speak a word or sentence')).to_be_enabled()
    assert page.evaluate('window.stoppedTracks') == 1 and not calls
    page.get_by_role('button', name='Speak a word or sentence').click()
    page.get_by_role('button', name='Stop and transcribe').click()
    expect(page.get_by_role('textbox', name='French vocabulary, one per line')).to_have_value('bonjour')
    assert len(calls) == 1 and 'language=FR' in calls[0]


def test_return_to_original_exercise_after_changing_add_language(page, server):
    page.route('**/api/typed', lambda route: route.fulfill(json={'source': 'test', 'questions': [{
        'term': 'banana', 'question': 'The answer is _____.', 'hint': 'A fruit', 'correctAnswer': 'banana',
        'completeSentence': 'The answer is banana.', 'englishTranslation': 'A sentence.'}]}))
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    answer = page.get_by_role('textbox', name='Your answer')
    answer.fill('ban')
    page.locator('header').get_by_role('link', name='Add').click()
    page.locator('header').get_by_role('button', name='FR', exact=True).click()
    expect(page).to_have_url(re.compile('/add$'))
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('ban')
    expect(page.locator('header').get_by_role('button', name='DE', exact=True)).to_have_attribute('aria-pressed', 'true')


def test_return_to_original_article_after_changing_add_language(page, server):
    article = {'topic': 'physics', 'title': 'Ein neuer Rekord', 'publication': 'Publisher',
               'url': 'https://example.com/article', 'publishedAt': '2026-10-29', 'retrievedAt': '2026-10-30',
               'summary': 'Forscher melden einen Rekord.', 'words': ['Rekord']}
    page.route('**/api/read', lambda route: route.fulfill(json=article))
    page.goto(server[0] + '/read')
    page.get_by_role('button', name='Retrieve', exact=False).click()
    expect(page.get_by_role('heading', name='Ein neuer Rekord')).to_be_visible()
    page.locator('header').get_by_role('link', name='Add').click()
    page.locator('header').get_by_role('button', name='FR', exact=True).click()
    page.get_by_role('link', name='Back to article').click()
    expect(page.get_by_role('heading', name='Ein neuer Rekord')).to_be_visible()
    expect(page.locator('header').get_by_role('button', name='DE', exact=True)).to_have_attribute('aria-pressed', 'true')


def test_language_shortcuts_and_legend_work_while_typing(page, server):
    page.goto(server[0] + '/add')
    header = page.locator('header')
    de = page.get_by_role('textbox', name='German vocabulary, one per line')
    de.fill('Text remains')
    de.press('Control+f')
    expect(header.get_by_role('button', name='FR', exact=True)).to_have_attribute('aria-pressed', 'true')
    expect(page).to_have_url(re.compile('/add$'))
    fr = page.get_by_role('textbox', name='French vocabulary, one per line')
    fr.fill('Bonjour')
    fr.press('Control+e')
    expect(header.get_by_role('button', name='EN', exact=True)).to_have_attribute('aria-pressed', 'true')
    en = page.get_by_role('textbox', name='English vocabulary, one per line')
    en.press('Control+d')
    expect(header.get_by_role('button', name='DE', exact=True)).to_have_attribute('aria-pressed', 'true')
    expect(de).to_have_value('Text remains')
    header.get_by_role('button', name=re.compile('^Languages menu')).click()
    page.get_by_role('menuitem', name='Keyboard shortcuts').click()
    dialog = page.get_by_role('dialog', name='Keyboard shortcuts')
    for key in ('Ctrl+E', 'Ctrl+D', 'Ctrl+F'):
        expect(dialog.get_by_text(key, exact=True)).to_be_visible()


def test_language_shortcut_from_exercise_preserves_progress(page, server):
    page.route('**/api/typed', lambda route: route.fulfill(json={'source': 'test', 'questions': [{
        'term': 'banana', 'question': 'The answer is _____.', 'hint': 'A fruit', 'correctAnswer': 'banana',
        'completeSentence': 'The answer is banana.', 'englishTranslation': 'A sentence.'}]}))
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    answer = page.get_by_role('textbox', name='Your answer')
    answer.fill('ban')
    answer.press('Control+f')
    expect(page).to_have_url(re.compile('/$'))
    expect(page.locator('header').get_by_role('button', name='FR', exact=True)).to_have_attribute('aria-pressed', 'true')
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name='Resume', exact=True).click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('ban')
    expect(page.locator('header').get_by_role('button', name='DE', exact=True)).to_have_attribute('aria-pressed', 'true')


def test_inflight_save_keeps_original_language_and_report(page, server):
    page.add_init_script('''
      const originalFetch = window.fetch.bind(window);
      window.fetch = (url, options) => {
        if (String(url) !== '/api/entries/save') return originalFetch(url, options);
        window.pendingLanguage = JSON.parse(options.body).language;
        return new Promise((resolve) => { window.finishSave = () => resolve(new Response(JSON.stringify({
          saved: [{term:'Wort', fileName:'german-1.md', termsInFile:13}],
          fileName:'german-1.md', termsInFile:13, fileFull:false
        }), {status:200, headers:{'Content-Type':'application/json'}})); });
      };
    ''')
    page.route('**/api/entries/define', lambda route: route.fulfill(json={
        'term': 'Wort', 'markdown': '## Wort\n\n**Definition:** Word.', 'gloss': 'word'}))
    page.goto(server[0] + '/add')
    page.get_by_role('textbox', name='German vocabulary, one per line').fill('Wort')
    page.get_by_role('button', name='Write entries').click()
    page.get_by_role('button', name='Add 1 entry').click()
    page.wait_for_function('typeof window.finishSave === "function"')
    assert page.evaluate('window.pendingLanguage') == 'DE'
    page.locator('header').get_by_role('button', name='FR', exact=True).click()
    page.evaluate('window.finishSave()')
    page.wait_for_timeout(200)
    expect(page.get_by_text(re.compile('Added 1 entry to'))).to_have_count(0)
    page.locator('header').get_by_role('button', name='DE', exact=True).click()
    expect(page.get_by_text('Added 1 entry to vocabulary/german/german-1.md')).to_be_visible()
