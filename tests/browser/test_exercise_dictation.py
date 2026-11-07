import re
import pytest
from playwright.sync_api import expect
from test_use_dictation import MOCK_RECORDER


QUIZ = {'term': 'apple', 'question': 'I have _____.', 'choices': ['an apple', 'a pear', 'a plum', 'a peach'], 'correctChoice': 0,
        'completeSentence': 'I have an apple.', 'englishTranslation': 'An apple.', 'choicesTranslations': []}
TYPED = {'term': 'apple', 'question': 'I have _____.', 'hint': 'A fruit', 'correctAnswer': 'an apple',
         'completeSentence': 'I have an apple.', 'englishTranslation': 'An apple.'}


def start(page, server, mode):
    endpoint = 'typed' if mode == 'produce' else 'quiz'
    page.route('**/api/' + endpoint, lambda route: route.fulfill(json={'source':'test', 'questions':[TYPED if mode == 'produce' else QUIZ]}))
    page.goto(server[0] + '/' + endpoint)
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    expect(page.get_by_role('button', name='Speak answer')).to_be_visible()


def record(page):
    page.get_by_role('button', name='Speak answer').click()
    expect(page.get_by_role('button', name='Stop and transcribe')).to_be_visible()
    page.get_by_role('button', name='Stop and transcribe').click()


@pytest.mark.parametrize('code', ['EN', 'DE', 'FR'])
def test_produce_dictation_can_be_reviewed_and_edited(page, server, code):
    page.add_init_script(MOCK_RECORDER)
    calls = []
    page.route('**/api/transcribe?*', lambda route: (calls.append(route.request.url), route.fulfill(json={'text':'an apple.'})))
    page.goto(server[0] + '/')
    page.locator('header').get_by_role('button', name=code, exact=True).click()
    start(page, server, 'produce')
    record(page)
    answer = page.get_by_role('textbox', name='Your answer')
    expect(answer).to_have_value('an apple.')
    answer.fill('an apple')
    expect(answer).to_have_value('an apple')
    assert f'language={code}' in calls[0]


def test_recognise_speech_requires_confirmation_of_choice(page, server):
    page.add_init_script(MOCK_RECORDER)
    page.route('**/api/transcribe?*', lambda route: route.fulfill(json={'text':'A PEAR.'}))
    start(page, server, 'recognise')
    record(page)
    expect(page.get_by_text('Heard:', exact=False)).to_contain_text('A PEAR.')
    confirm = page.get_by_role('button', name='Choose B: a pear')
    expect(confirm).to_be_visible()
    expect(page.get_by_label('Feedback')).to_have_count(0)
    confirm.click()
    expect(page.get_by_label('Feedback')).to_be_visible()


def test_recognise_does_not_guess_unmatched_transcript(page, server):
    page.add_init_script(MOCK_RECORDER)
    page.route('**/api/transcribe?*', lambda route: route.fulfill(json={'text':'a banana'}))
    start(page, server, 'recognise')
    record(page)
    expect(page.get_by_role('status').filter(has_text='No single choice matched')).to_be_visible()
    expect(page.get_by_label('Feedback')).to_have_count(0)


@pytest.mark.parametrize('mode', ['recognise', 'produce'])
def test_speaking_sentence_fills_and_submits_the_blank(page, server, mode):
    page.add_init_script(MOCK_RECORDER)
    page.route('**/api/transcribe?*', lambda route: route.fulfill(json={'text': 'I have an apple.'}))
    checked = []
    page.route('**/api/typed/check', lambda route: (checked.append(route.request.post_data_json), route.fulfill(json={
        'verdict':'correct', 'correctedAnswer':'an apple', 'errors':[], 'comment':'', 'suggestions':[], 'notice':None})))
    start(page, server, mode)
    page.get_by_role('button', name='Speak sentence').click()
    page.get_by_role('button', name='Stop and transcribe').click()
    sentence = page.get_by_role('textbox', name='Review the sentence')
    expect(sentence).to_have_value('I have an apple.')
    expect(page.get_by_label('Feedback')).to_have_count(0)
    page.get_by_role('button', name='OK', exact=True).click()
    expect(page.get_by_label('Feedback')).to_be_visible()
    if mode == 'produce':
        assert checked[0]['answer'] == 'an apple'


def test_sentence_with_missing_context_can_be_corrected_before_submission(page, server):
    page.add_init_script(MOCK_RECORDER)
    page.route('**/api/transcribe?*', lambda route: route.fulfill(json={'text': 'a banana'}))
    start(page, server, 'recognise')
    page.get_by_role('button', name='Speak sentence').click()
    page.get_by_role('button', name='Stop and transcribe').click()
    sentence = page.get_by_role('textbox', name='Review the sentence')
    expect(sentence).to_have_value('a banana')
    page.get_by_role('button', name='OK', exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('Could not match')
    expect(page.get_by_label('Feedback')).to_have_count(0)
    sentence.fill('I have a pear.')
    page.get_by_role('button', name='OK', exact=True).click()
    expect(page.get_by_label('Feedback')).to_be_visible()


def test_spoken_sentence_handles_french_contraction(page, server):
    page.add_init_script(MOCK_RECORDER)
    question = {'term':'heure', 'question':'C’est l’_____ de la journée.', 'hint':'Time', 'correctAnswer':'heure',
                'completeSentence':'C’est l’heure de la journée.', 'englishTranslation':'It is the time of day.'}
    page.route('**/api/typed', lambda route: route.fulfill(json={'source':'test', 'questions':[question]}))
    page.route('**/api/transcribe?*', lambda route: route.fulfill(json={'text': "C'est l'heure de la journée."}))
    checked = []
    page.route('**/api/typed/check', lambda route: (checked.append(route.request.post_data_json), route.fulfill(json={
        'verdict':'correct', 'correctedAnswer':'heure', 'errors':[], 'comment':'', 'suggestions':[], 'notice':None})))
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('button', name='Speak sentence').click()
    page.get_by_role('button', name='Stop and transcribe').click()
    expect(page.get_by_role('textbox', name='Review the sentence')).to_be_visible()
    page.get_by_role('button', name='OK', exact=True).click()
    expect(page.get_by_label('Feedback')).to_be_visible()
    assert checked[0]['answer'] == 'heure'
