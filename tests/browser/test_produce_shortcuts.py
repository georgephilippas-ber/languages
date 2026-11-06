import re
from playwright.sync_api import expect


def test_produce_shortcuts_reveal_hint_and_follow_letter_rules(page, server):
    url, _ = server
    page.route('**/api/typed', lambda route: route.fulfill(json={'source': 'synthetic', 'questions': [{
        'term': 'banana', 'question': 'The answer is _____.', 'hint': 'A yellow fruit',
        'correctAnswer': 'banana', 'completeSentence': 'The answer is banana.', 'englishTranslation': 'A sentence.'}]}))
    page.goto(url + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    input_ = page.get_by_role('textbox', name='Your answer')
    expect(input_).to_be_focused()
    hint = page.get_by_role('button', name=re.compile('Meaning hint'))
    expect(hint).to_have_attribute('aria-expanded', 'false')
    page.keyboard.press('Control+h')
    expect(hint).to_have_attribute('aria-expanded', 'true')
    expect(page.get_by_text('A yellow fruit')).to_be_visible()
    page.keyboard.press('Control+h')
    expect(hint).to_have_attribute('aria-expanded', 'true')
    letters = page.locator('[aria-label="Revealed letters"]')
    page.keyboard.press('Control+l')
    expect(letters).to_have_text('b•••••')
    page.evaluate('Math.random = () => 0')
    page.keyboard.press('Control+l')
    expect(letters).to_have_text('ba•a•a')
    page.keyboard.press('Control+l')
    expect(letters).to_have_text('banana')
    page.keyboard.press('Control+l')
    expect(letters).to_have_text('banana')
    expect(page.get_by_role('button', name=re.compile('Reveal letter'))).to_be_disabled()
    expect(input_).to_have_value('')
