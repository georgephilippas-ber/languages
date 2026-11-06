import re

from playwright.sync_api import expect


def test_saved_produce_question_hides_labelled_hint(page, server):
    url, _ = server
    question = 'After months without pruning, the balcony plants looked _____ rather than thick and healthy. (Hint: thin, uneven, and untidy in growth.)'
    clean = 'After months without pruning, the balcony plants looked _____ rather than thick and healthy.'
    complete = clean.replace('_____', 'straggly')
    page.route('**/api/typed', lambda route: route.fulfill(json={
        'source': 'synthetic', 'questions': [{'term': 'straggly', 'question': question, 'hint': 'A meaning',
                                              'correctAnswer': 'straggly', 'completeSentence': complete + ' (Hint: thin.)',
                                              'englishTranslation': 'A sentence.'}]}))
    checked = []
    def check(route):
        checked.append(route.request.post_data_json['question'])
        route.fulfill(json={'verdict': 'correct', 'correctedAnswer': 'straggly', 'errors': [],
                            'comment': '', 'suggestions': [], 'notice': None})
    page.route('**/api/typed/check', check)
    page.goto(url + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    expect(page.get_by_role('textbox', name='Your answer')).to_be_visible()
    expect(page.get_by_text('Hint: thin, uneven', exact=False)).to_have_count(0)
    expect(page.get_by_text('rather than thick and healthy.', exact=False)).to_be_visible()
    page.wait_for_function("() => localStorage.getItem('languages.session.typed') !== null")
    page.reload()
    page.get_by_role('button', name='Resume', exact=True).click()
    expect(page.get_by_text('Hint: thin, uneven', exact=False)).to_have_count(0)
    page.get_by_role('textbox', name='Your answer').fill('straggly')
    page.get_by_role('button', name=re.compile(r'^Check')).click()
    expect(page.get_by_label('Feedback')).to_be_visible()
    assert checked[0]['question'] == clean
    assert checked[0]['completeSentence'] == complete
    expect(page.get_by_text('Hint: thin.', exact=False)).to_have_count(0)
