import re
from playwright.sync_api import expect


def test_navigation_shortcuts_from_textboxes_preserve_drafts_and_legend(page, server):
    page.goto(server[0] + '/')
    expect(page.locator('header').get_by_role('link', name='Add')).to_be_visible()
    page.keyboard.press('Control+a')
    expect(page).to_have_url(re.compile('/add$'))
    add = page.get_by_role('textbox', name='German vocabulary, one per line')
    add.fill('unsubmitted words')
    add.press('Control+s')
    expect(page).to_have_url(re.compile('/ask$'))
    ask = page.get_by_role('textbox', name='Your question')
    ask.fill('unsubmitted question')
    ask.press('Control+a')
    expect(page).to_have_url(re.compile('/add$'))
    expect(page.get_by_role('textbox', name='German vocabulary, one per line')).to_have_value('unsubmitted words')
    page.get_by_role('textbox', name='German vocabulary, one per line').press('Control+s')
    expect(page.get_by_role('textbox', name='Your question')).to_have_value('unsubmitted question')
    page.locator('header').get_by_role('button', name=re.compile('^Languages menu')).click()
    page.get_by_role('menuitem', name='Keyboard shortcuts').click()
    dialog = page.get_by_role('dialog', name='Keyboard shortcuts')
    expect(dialog).to_be_visible()
    for label in ['Ctrl+A', 'Ctrl+S', 'Ctrl+H', 'Ctrl+L']:
        expect(dialog.get_by_text(label, exact=True)).to_be_visible()
    page.keyboard.press('Control+a')
    expect(page).to_have_url(re.compile('/ask$'))
    dialog.get_by_role('button', name='Close').click()
    page.keyboard.press('Control+a')
    expect(page).to_have_url(re.compile('/add$'))
    expect(page.get_by_role('textbox', name='German vocabulary, one per line')).to_have_value('unsubmitted words')


def test_shortcuts_from_exercise_textbox_preserve_resume(page, server):
    page.route('**/api/typed', lambda route: route.fulfill(json={'source': 'test', 'questions': [{
        'term': 'banana', 'question': 'The answer is _____.', 'hint': 'A fruit', 'correctAnswer': 'banana',
        'completeSentence': 'The answer is banana.', 'englishTranslation': 'A sentence.'}]}))
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    text = page.get_by_role('textbox', name='Your answer')
    text.fill('ban')
    text.press('Control+a')
    expect(page).to_have_url(re.compile('/add$'))
    page.get_by_role('textbox', name='German vocabulary, one per line').press('Control+s')
    expect(page).to_have_url(re.compile('/ask$'))
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('ban')


def test_read_text_survives_shortcut_and_browser_back(page, server):
    page.goto(server[0] + '/read?mode=text')
    source = page.get_by_role('textbox', name='Article text')
    source.fill('A passage not yet submitted.')
    source.press('Control+s')
    expect(page).to_have_url(re.compile('/ask$'))
    page.go_back()
    expect(page.get_by_role('textbox', name='Article text')).to_have_value('A passage not yet submitted.')


def test_homepage_summary_contains_only_language_and_total(page, server):
    page.goto(server[0] + '/')
    summary = page.locator('main').get_by_text(re.compile(r'^German · \d+ terms?$'))
    expect(summary).to_be_visible()
    assert 'files' not in summary.inner_text() and 'batch' not in summary.inner_text()


def test_homepage_heading_uses_one_line_when_it_fits(page, server):
    page.set_viewport_size({'width': 1440, 'height': 800})
    page.goto(server[0] + '/')
    heading = page.get_by_role('heading', name='Your words, in working order.')
    expect(heading).to_be_visible()
    lines = heading.evaluate('''(el) => {
      const range = document.createRange(); range.selectNodeContents(el);
      return new Set([...range.getClientRects()].filter(r => r.width > 0).map(r => Math.round(r.top))).size;
    }''')
    assert lines == 1
    page.set_viewport_size({'width': 320, 'height': 800})
    assert page.locator('body').evaluate('(el) => el.scrollWidth <= el.clientWidth')
    lines = heading.evaluate('''(el) => {
      const range = document.createRange(); range.selectNodeContents(el);
      return new Set([...range.getClientRects()].filter(r => r.width > 0).map(r => Math.round(r.top))).size;
    }''')
    assert lines > 1


def test_add_and_ask_focus_textbox_on_open(page, server):
    page.goto(server[0] + '/')
    page.locator('header').get_by_role('link', name='Add').click()
    expect(page.get_by_role('textbox', name='German vocabulary, one per line')).to_be_focused()
    page.locator('header').get_by_role('link', name='Ask').click()
    expect(page.get_by_role('textbox', name='Your question')).to_be_focused()
    page.get_by_role('textbox', name='Your question').fill('A question')
    page.locator('header').get_by_role('link', name='Add').click()
    expect(page.get_by_role('textbox', name='German vocabulary, one per line')).to_be_focused()


def test_ctrl_s_from_focused_empty_add_opens_ask(page, server):
    page.goto(server[0] + '/add')
    text = page.get_by_role('textbox', name='German vocabulary, one per line')
    expect(text).to_be_focused()
    text.press('Control+s')
    expect(page).to_have_url(re.compile('/ask$'))
    expect(page.get_by_role('textbox', name='Your question')).to_be_focused()


def test_submitted_drafts_are_cleared_and_not_reused(page, server):
    page.route('**/api/entries/define', lambda route: route.fulfill(json={'term': 'Wort', 'markdown': '## Wort\n\n**Definition:** Word.', 'gloss': 'word'}))
    page.route('**/api/ask', lambda route: route.fulfill(json={'answer': 'An answer.', 'onTopic': True}))
    page.goto(server[0] + '/add')
    text = page.get_by_role('textbox', name='German vocabulary, one per line')
    text.fill('Wort')
    page.get_by_role('button', name='Write entries').click()
    expect(text).to_have_value('')
    text.press('Control+s')
    question = page.get_by_role('textbox', name='Your question')
    question.fill('What is this word?')
    page.locator('main').get_by_role('button', name=re.compile('^Ask')).click()
    expect(question).to_have_value('')
    expect(page.get_by_text('An answer.')).to_be_visible()
    question.press('Control+a')
    expect(page.get_by_role('textbox', name='German vocabulary, one per line')).to_have_value('')
    page.get_by_role('textbox', name='German vocabulary, one per line').press('Control+s')
    expect(page.get_by_role('textbox', name='Your question')).to_have_value('')
