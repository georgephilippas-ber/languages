import re
from playwright.sync_api import expect


def test_navigation_shortcuts_and_legend(page, server):
    page.goto(server[0] + '/')
    expect(page.locator('header').get_by_role('link', name='Add')).to_be_visible()
    page.keyboard.press('Control+a')
    expect(page).to_have_url(re.compile('/add$'))
    text = page.get_by_role('textbox', name='German vocabulary, one per line')
    text.fill('unsubmitted words')
    text.press('Control+a')
    expect(page).to_have_url(re.compile('/add$'))
    expect(text).to_have_value('unsubmitted words')
    text.press('Control+s')
    expect(page).to_have_url(re.compile('/add$'))
    text.blur()
    page.keyboard.press('Control+s')
    expect(page).to_have_url(re.compile('/ask$'))
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


def test_shortcut_from_exercise_preserves_resume_and_ctrl_a_edits(page, server):
    page.route('**/api/typed', lambda route: route.fulfill(json={'source': 'test', 'questions': [{
        'term': 'banana', 'question': 'The answer is _____.', 'hint': 'A fruit', 'correctAnswer': 'banana',
        'completeSentence': 'The answer is banana.', 'englishTranslation': 'A sentence.'}]}))
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    text = page.get_by_role('textbox', name='Your answer')
    text.fill('ban')
    text.press('Control+a')
    expect(page).to_have_url(re.compile('/typed$'))
    expect(text).to_have_value('ban')
    text.press('Control+s')
    expect(page).to_have_url(re.compile('/ask$'))
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('ban')


def test_homepage_summary_contains_only_language_and_total(page, server):
    page.goto(server[0] + '/')
    summary = page.locator('main').get_by_text(re.compile(r'^German · \d+ terms?$'))
    expect(summary).to_be_visible()
    assert 'files' not in summary.inner_text() and 'batch' not in summary.inner_text()
