import re
from playwright.sync_api import expect


def test_english_quiz_feedback_shows_explanation(page, server):
    url, _ = server
    page.route('**/api/quiz', lambda route: route.fulfill(json={'source': 'synthetic', 'questions': [{
        'term': 'to bring about', 'question': 'The new rules will _____ lower fees.',
        'choices': ['bring about', 'bring up'], 'correctChoice': 0,
        'completeSentence': 'The new rules will bring about lower fees.',
        'englishTranslation': 'Cause a reduction in fees.', 'choicesTranslations': ['cause', 'mention']}]}))
    page.goto(url + '/')
    page.get_by_role('button', name='EN', exact=True).click()
    page.goto(url + '/quiz')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('button', name=re.compile('bring about')).first.click()
    expect(page.get_by_text('Explanation', exact=True)).to_be_visible()
    expect(page.get_by_text('Cause a reduction in fees.')).to_be_visible()
    expect(page.get_by_text('Translation', exact=True)).to_have_count(0)
