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
