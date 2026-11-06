import re

from playwright.sync_api import expect


def serve_question(page, hint):
    page.route('**/api/typed', lambda route: route.fulfill(json={
        'source': 'synthetic', 'questions': [
            {'term': 'banana', 'question': 'Here is _____.', 'hint': hint, 'correctAnswer': 'banana',
             'completeSentence': 'Here is banana.', 'englishTranslation': 'A sentence.'}]}))


def test_meaning_hint_is_hidden_and_click_to_toggle(page, server):
    url, _ = server
    serve_question(page, 'A yellow fruit')
    page.goto(url + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    button = page.get_by_role('button', name=re.compile(r'^Meaning hint'))
    hint = page.get_by_text('A yellow fruit', exact=True)
    expect(button).to_have_attribute('aria-expanded', 'false')
    expect(hint).to_be_hidden()
    button.hover()
    expect(button).to_have_attribute('aria-expanded', 'false')
    expect(hint).to_be_hidden()
    button.click()
    expect(hint).to_be_visible()
    button.click()
    expect(hint).to_be_hidden()


def test_saved_hint_with_answer_is_withheld(page, server):
    url, _ = server
    serve_question(page, 'A BANANA is a fruit')
    page.goto(url + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    expect(page.get_by_role('button', name=re.compile(r'^Meaning hint'))).to_be_visible()
    page.wait_for_function("() => localStorage.getItem('languages.session.typed') !== null")
    page.reload()
    page.get_by_role('button', name='Resume', exact=True).click()
    button = page.get_by_role('button', name=re.compile(r'^Meaning hint'))
    expect(button).to_have_attribute('aria-expanded', 'false')
    button.click()
    assert page.locator('#' + button.get_attribute('aria-controls')).inner_text() == '—'
    expect(page.get_by_text('A BANANA is a fruit', exact=True)).to_have_count(0)


def test_saved_hint_with_accent_variant_is_withheld(page, server):
    url, _ = server
    page.route('**/api/typed', lambda route: route.fulfill(json={
        'source': 'synthetic', 'questions': [
            {'term': 'die Straße', 'question': 'Hier ist _____.', 'hint': 'The STRASSE is a road',
             'correctAnswer': 'Straßen', 'completeSentence': 'Hier ist Straßen.', 'englishTranslation': 'A sentence.'}]}))
    page.goto(url + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    button = page.get_by_role('button', name=re.compile(r'^Meaning hint'))
    button.click()
    assert page.locator('#' + button.get_attribute('aria-controls')).inner_text() == '—'
    expect(page.get_by_text('The STRASSE is a road', exact=True)).to_have_count(0)
