import json
import re
import pytest
from playwright.sync_api import expect

QUIZ = {'term': 'term', 'question': 'This is _____.', 'choices': ['one', 'two', 'three', 'four'], 'correctChoice': 0,
        'completeSentence': 'This is one.', 'englishTranslation': 'One item.', 'choicesTranslations': []}
TYPED = {'term': 'term', 'question': 'This is _____.', 'hint': 'An item', 'correctAnswer': 'one',
         'completeSentence': 'This is one.', 'englishTranslation': 'One item.'}
MIXED = {'sourceLanguage': 'FR', 'targetLanguage': 'DE', 'sourceSentence': 'Le chat dort.',
         'segments': ['Die ', ' schläft.'], 'answers': ['Katze'], 'hint': 'An animal',
         'choices': [['Katze'], ['Maus'], ['Vogel'], ['Frau']], 'correctChoice': 0, 'terms': ['le chat']}


@pytest.mark.parametrize('numbers,path,endpoint,language,mode', [
    ([0.0], '/quiz', 'quiz', 'DE', None),
    ([0.5], '/typed', 'typed', 'DE', None),
    ([0.9, 0.1], '/translate/recognize', 'mixed-translation', None, 'recognize'),
    ([0.9, 0.9], '/translate/produce', 'mixed-translation', None, 'produce'),
])
def test_lucky_starts_twelve_c1_questions(page, server, numbers, path, endpoint, language, mode):
    requests = []
    item = {'quiz': QUIZ, 'typed': TYPED, 'mixed-translation': MIXED}[endpoint]
    def generate(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json={'source': 'test', 'questions': [item] * 12})
    page.route('**/api/' + endpoint, generate)
    page.goto(server[0] + '/')
    page.evaluate("localStorage.setItem('languages.settings.quiz', JSON.stringify({level:'A1',count:3,files:'current'}))")
    page.evaluate("localStorage.setItem('languages.session.writing', JSON.stringify({sentinel:'keep'}))")
    page.evaluate('(numbers) => { const values = [...numbers]; Math.random = () => values.shift() ?? 0; }', numbers)
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    expect(page).to_have_url(re.compile(re.escape(path) + '$'))
    expect(page.get_by_role('progressbar')).to_have_attribute('aria-label', '0 of 12 answered')
    assert requests[-1]['count'] == 12 and requests[-1]['level'] == 'C1'
    if mode:
        assert requests[-1]['mode'] == mode and requests[-1]['includePhrasal'] is False
        assert requests[-1]['pairLanguage'] == 'DE'
    else:
        assert requests[-1]['language'] == language and requests[-1]['files'] == 'all'
        expect(page.get_by_role('button', name=language, exact=True)).to_have_attribute('aria-pressed', 'true')
    assert json.loads(page.evaluate("localStorage.getItem('languages.session.writing')")) == {'sentinel': 'keep'}


def test_lucky_does_not_start_with_fewer_than_twelve(page, server):
    requests = []
    def generate(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json={'source': 'test', 'questions': [QUIZ] * 2})
    page.route('**/api/quiz', generate)
    page.goto(server[0] + '/')
    page.evaluate('Math.random = () => 0')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    expect(page.get_by_role('alert')).to_contain_text('Only 2 of 12 questions were generated')
    page.get_by_role('button', name='Try again').click()
    expect(page.get_by_role('alert')).to_contain_text('Only 2 of 12 questions were generated')
    assert len(requests) == 2 and all(request['count'] == 12 for request in requests)


def test_lucky_button_in_header_uses_the_same_settings(page, server):
    requests = []
    def generate(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json={'source': 'test', 'questions': [QUIZ] * 12})
    page.route('**/api/quiz', generate)
    page.goto(server[0] + '/read')
    page.evaluate('Math.random = () => 0')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    expect(page).to_have_url(re.compile('/quiz$'))
    expect(page.get_by_role('progressbar')).to_have_attribute('aria-label', '0 of 12 answered')
    assert requests[-1]['count'] == 12 and requests[-1]['level'] == 'C1' and requests[-1]['language'] == 'DE'


@pytest.mark.parametrize('code', ['EN', 'DE', 'FR'])
@pytest.mark.parametrize('mode,endpoint,question', [(0.0, 'quiz', QUIZ), (0.5, 'typed', TYPED)])
def test_lucky_single_language_keeps_selected_language(page, server, code, mode, endpoint, question):
    requests = []
    page.route('**/api/' + endpoint, lambda route: (requests.append(route.request.post_data_json), route.fulfill(json={'source': 'test', 'questions': [question] * 12})))
    page.goto(server[0] + '/')
    page.locator('header').get_by_role('button', name=code, exact=True).click()
    page.evaluate('(value) => { Math.random = () => value }', mode)
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    expect(page.get_by_role('progressbar')).to_be_visible()
    assert requests[0]['language'] == code and requests[0]['count'] == 12 and requests[0]['level'] == 'C1'
    expect(page.locator('header').get_by_role('button', name=code, exact=True)).to_have_attribute('aria-pressed', 'true')


def test_lucky_uses_translation_if_selected_language_has_too_few_terms(page, server):
    requests = []
    def metadata(route):
        response = route.fetch(); body = response.json()
        next(lang for lang in body['languages'] if lang['code'] == 'DE')['files'] = []
        route.fulfill(response=response, json=body)
    page.route('**/api/meta', metadata)
    page.route('**/api/mixed-translation', lambda route: (requests.append(route.request.post_data_json), route.fulfill(json={'source': 'test', 'questions': [MIXED] * 12})))
    page.goto(server[0] + '/')
    page.evaluate('Math.random = () => 0')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    expect(page).to_have_url(re.compile('/translate/recognize$'))
    expect(page.get_by_role('progressbar')).to_be_visible()
    assert requests[0]['count'] == 12 and requests[0]['mode'] == 'recognize'
    expect(page.locator('header').get_by_role('button', name='DE', exact=True)).to_have_attribute('aria-pressed', 'true')


@pytest.mark.parametrize('code', ['DE', 'FR'])
def test_lucky_translation_requests_selected_language_with_english(page, server, code):
    requests = []
    page.route('**/api/mixed-translation', lambda route: (requests.append(route.request.post_data_json), route.fulfill(json={'source': 'test', 'questions': [MIXED] * 12})))
    page.goto(server[0] + '/')
    page.locator('header').get_by_role('button', name=code, exact=True).click()
    page.evaluate('Math.random = () => 0.99')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    expect(page.get_by_role('progressbar')).to_be_visible()
    assert requests[0]['pairLanguage'] == code


def test_lucky_english_never_selects_translation(page, server):
    requests = []
    page.route('**/api/typed', lambda route: (requests.append(route.request.post_data_json), route.fulfill(json={'source': 'test', 'questions': [TYPED] * 12})))
    page.goto(server[0] + '/')
    page.locator('header').get_by_role('button', name='EN', exact=True).click()
    page.evaluate('Math.random = () => 0.99')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    expect(page).to_have_url(re.compile('/typed$'))
    expect(page.get_by_role('progressbar')).to_be_visible()
    assert requests[0]['language'] == 'EN'
