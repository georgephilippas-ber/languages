import re
from playwright.sync_api import expect


def setup_typed(page):
    requests = []
    def generate(route):
        requests.append(route.request.post_data_json)
        word = 'banana' if len(requests) == 1 else 'second'
        question = {'term': word, 'question': f'Word {word} is _____.', 'hint': 'A meaning',
                    'correctAnswer': word, 'completeSentence': f'Word {word} is {word}.', 'englishTranslation': 'A sentence.'}
        route.fulfill(json={'source': 'test', 'questions': [question] * 12})
    page.route('**/api/typed', generate)
    page.route('**/api/typed/check', lambda route: route.fulfill(json={
        'verdict': 'correct', 'correctedAnswer': route.request.post_data_json['answer'], 'errors': [],
        'comment': '', 'suggestions': [], 'notice': None}))
    return requests


def start_lucky_typed(page, server):
    page.goto(server[0] + '/')
    page.evaluate('Math.random = () => 0.5')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    expect(page).to_have_url(re.compile('/typed$'))
    expect(page.get_by_role('textbox', name='Your answer')).to_be_visible()


def test_lucky_offers_resume_after_add_with_answer_and_hint(page, server):
    requests = setup_typed(page)
    start_lucky_typed(page, server)
    page.get_by_role('textbox', name='Your answer').fill('ban')
    page.get_by_role('button', name=re.compile('^Reveal letter')).click()
    page.locator('header').get_by_role('link', name='Add').click()
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    dialog = page.get_by_role('dialog', name='Continue Lucky?')
    expect(dialog).to_be_visible()
    expect(dialog).to_contain_text('Produce')
    expect(dialog).to_contain_text('question 1 of 12')
    dialog.get_by_role('button', name='Resume', exact=True).click()
    expect(page).to_have_url(re.compile('/typed$'))
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('ban')
    expect(page.get_by_role('button', name=re.compile('^Reveal letter'))).to_contain_text('1/3')
    assert len(requests) == 1


def test_lucky_survives_starting_another_exercise_of_same_kind(page, server):
    requests = setup_typed(page)
    start_lucky_typed(page, server)
    page.get_by_role('textbox', name='Your answer').fill('saved lucky')
    page.locator('header').get_by_role('link', name='Home').click()
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    expect(page.get_by_text('Word second is', exact=False)).to_be_visible()
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    page.get_by_role('dialog', name='Continue Lucky?').get_by_role('button', name='Resume').click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('saved lucky')
    assert len(requests) == 2


def test_start_new_from_same_exercise_and_finish_clears_lucky(page, server):
    requests = setup_typed(page)
    start_lucky_typed(page, server)
    page.get_by_role('textbox', name='Your answer').fill('old')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    dialog = page.get_by_role('dialog', name='Continue Lucky?')
    dialog.get_by_role('button', name='Start new').click()
    expect(page.get_by_text('Word second is', exact=False)).to_be_visible()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('')
    assert len(requests) == 2
    page.get_by_role('button', name='End exercise').click()
    page.get_by_role('button', name='End and see results').click()
    expect(page.get_by_text('Nothing answered')).to_be_visible()
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    expect(page.get_by_role('dialog', name='Continue Lucky?')).not_to_be_visible()
    expect(page.get_by_role('textbox', name='Your answer')).to_be_visible()
    assert len(requests) == 3


def test_legacy_lucky_session_can_resume(page, server):
    setup_typed(page)
    page.goto(server[0] + '/')
    page.evaluate('''() => {
      const item = {term:'old',question:'Legacy _____.',hint:'old clue',correctAnswer:'old',completeSentence:'Legacy old.',englishTranslation:'old.'};
      localStorage.removeItem('languages.lucky.session'); localStorage.removeItem('languages.lucky.migrated');
      localStorage.setItem('languages.session.typed', JSON.stringify({version:1,request:{language:'DE',level:'C1',count:12,files:'all'},
        source:'legacy',items:[item],records:[null],index:0,finished:false,requireFullCount:true,drafts:{0:'previous'}}));
    }''')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    page.get_by_role('dialog', name='Continue Lucky?').get_by_role('button', name='Resume').click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('previous')


def test_resume_lucky_restores_original_language_after_switch(page, server):
    requests = setup_typed(page)
    start_lucky_typed(page, server)
    page.get_by_role('textbox', name='Your answer').fill('ban')
    page.locator('header').get_by_role('link', name='Add').click()
    page.locator('header').get_by_role('button', name='FR', exact=True).click()
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    dialog = page.get_by_role('dialog', name='Continue Lucky?')
    expect(dialog).to_contain_text('German')
    dialog.get_by_role('button', name='Resume').click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('ban')
    expect(page.locator('header').get_by_role('button', name='DE', exact=True)).to_have_attribute('aria-pressed', 'true')
    assert len(requests) == 1


def test_mixed_lucky_resumes_both_typed_blanks(page, server):
    calls = []
    question = {'sourceLanguage': 'DE', 'targetLanguage': 'EN', 'sourceSentence': 'Die Katze sieht den Hund.',
                'segments': ['The ', ' sees the ', '.'], 'answers': ['cat', 'dog'], 'hint': 'Two animals',
                'choices': [['cat', 'dog'], ['cat', 'bird'], ['dog', 'cat'], ['bird', 'dog']],
                'correctChoice': 0, 'terms': ['die Katze', 'der Hund']}
    page.route('**/api/mixed-translation', lambda route: (calls.append(1), route.fulfill(json={'source': 'test', 'questions': [question] * 12})))
    page.goto(server[0] + '/')
    page.evaluate('Math.random = () => 0.9')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    first = page.get_by_role('textbox', name='Translation blank 1')
    second = page.get_by_role('textbox', name='Translation blank 2')
    first.fill('ca'); second.fill('do')
    page.locator('header').get_by_role('link', name='Ask').click()
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    dialog = page.get_by_role('dialog', name='Continue Lucky?')
    expect(dialog).to_contain_text('mixed languages')
    dialog.get_by_role('button', name='Resume').click()
    expect(page.get_by_role('textbox', name='Translation blank 1')).to_have_value('ca')
    expect(page.get_by_role('textbox', name='Translation blank 2')).to_have_value('do')
    assert len(calls) == 1


def test_failed_new_lucky_keeps_previous_progress(page, server):
    calls = []
    question = {'term': 'banana', 'question': 'Word banana is _____.', 'hint': 'Fruit',
                'correctAnswer': 'banana', 'completeSentence': 'Word banana is banana.', 'englishTranslation': 'A sentence.'}
    def generate(route):
        calls.append(1)
        route.fulfill(json={'source': 'test', 'questions': [question] * (12 if len(calls) == 1 else 2)})
    page.route('**/api/typed', generate)
    start_lucky_typed(page, server)
    page.get_by_role('textbox', name='Your answer').fill('saved')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    page.get_by_role('dialog', name='Continue Lucky?').get_by_role('button', name='Start new').click()
    expect(page.get_by_role('alert')).to_contain_text('Only 2 of 12 questions')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    page.get_by_role('dialog', name='Continue Lucky?').get_by_role('button', name='Resume').click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('saved')
    assert len(calls) == 2


def test_resuming_lucky_preserves_a_separate_regular_exercise(page, server):
    requests = setup_typed(page)
    start_lucky_typed(page, server)
    page.get_by_role('textbox', name='Your answer').fill('lucky answer')
    page.locator('header').get_by_role('link', name='Home').click()
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    normal = page.get_by_role('textbox', name='Your answer')
    normal.fill('regular answer')
    page.locator('header').get_by_role('button', name='I feel lucky').click()
    page.get_by_role('dialog', name='Continue Lucky?').get_by_role('button', name='Resume').click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('lucky answer')
    page.locator('header').get_by_role('link', name='Add').click()
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('lucky answer')
    page.locator('header').get_by_role('link', name='Home').click()
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name='Resume', exact=True).click()
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('regular answer')
    assert len(requests) == 2
