import re
from playwright.sync_api import expect


def test_produce_return_preserves_answer_hints_and_pauses_timer(page, server):
    calls = []
    def questions(route):
        calls.append(1)
        route.fulfill(json={'source': 'test', 'questions': [{'term': 'banana', 'question': 'The answer is _____.', 'hint': 'A fruit',
            'correctAnswer': 'banana', 'completeSentence': 'The answer is banana.', 'englishTranslation': 'A sentence.'}]})
    page.route('**/api/typed', questions)
    page.goto(server[0] + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('textbox', name='Your answer').fill('ban')
    page.get_by_role('button', name=re.compile('^Reveal letter')).click()
    page.locator('header').get_by_role('link', name='Add').click()
    back = page.get_by_role('link', name='Back to exercise')
    expect(back).to_be_visible()
    before = page.evaluate("JSON.parse(localStorage.getItem('languages.session.typed')).elapsed.ms")
    page.wait_for_timeout(1300)
    page.locator('header').get_by_role('link', name='Ask').click()
    expect(page.get_by_role('link', name='Back to exercise')).to_be_visible()
    page.get_by_role('link', name='Back to exercise').click()
    expect(page).to_have_url(re.compile('/typed$'))
    expect(page.get_by_role('textbox', name='Your answer')).to_have_value('ban')
    expect(page.get_by_role('button', name=re.compile('^Reveal letter'))).to_contain_text('1/3')
    assert len(calls) == 1
    page.locator('header').get_by_role('link', name='Ask').click()
    after = page.evaluate("JSON.parse(localStorage.getItem('languages.session.typed')).elapsed.ms")
    assert after - before < 1100


def test_return_preserves_answered_question_and_no_button_without_exercise(page, server):
    calls = []
    question = {'term': 'one', 'question': 'This is _____.', 'choices': ['one', 'two'], 'correctChoice': 0,
                'completeSentence': 'This is one.', 'englishTranslation': 'One thing.', 'choicesTranslations': []}
    page.route('**/api/quiz', lambda route: (calls.append(1), route.fulfill(json={'source': 'test', 'questions': [question]})))
    page.goto(server[0] + '/add')
    expect(page.get_by_role('link', name='Back to exercise')).to_have_count(0)
    page.goto(server[0] + '/quiz')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('button', name='A one').click()
    expect(page.get_by_role('region', name='Feedback')).to_be_visible()
    page.locator('header').get_by_role('link', name='Ask').click()
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_role('region', name='Feedback')).to_be_visible()
    assert len(calls) == 1


def test_mixed_translation_returns_with_both_partial_answers(page, server):
    question = {'sourceLanguage': 'DE', 'targetLanguage': 'EN', 'sourceSentence': 'Die Katze sieht den Hund.',
                'segments': ['The ', ' sees the ', '.'], 'answers': ['cat', 'dog'], 'hint': 'Two animals',
                'choices': [['cat', 'dog'], ['cat', 'bird'], ['dog', 'cat'], ['bird', 'dog']],
                'correctChoice': 0, 'terms': ['die Katze', 'der Hund']}
    page.route('**/api/mixed-translation', lambda route: route.fulfill(json={'source': 'Mixed', 'questions': [question]}))
    page.goto(server[0] + '/translate/produce')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('textbox', name='Translation blank 1').fill('ca')
    page.get_by_role('textbox', name='Translation blank 2').fill('do')
    page.locator('header').get_by_role('link', name='Add').click()
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_role('textbox', name='Translation blank 1')).to_have_value('ca')
    expect(page.get_by_role('textbox', name='Translation blank 2')).to_have_value('do')


def test_review_returns_to_revealed_card(page, server):
    card = {'term': 'die Sache', 'fileName': 'german-1.md', 'sections': [{'label': 'Definition', 'text': 'A thing'}],
            'state': {'dueAt': None}, 'isNew': True, 'isDue': False, 'intervals': {}}
    page.route('**/api/flashcards', lambda route: route.fulfill(json={'source': 'test', 'cards': [card]}))
    page.goto(server[0] + '/review')
    page.get_by_role('button', name='Browse', exact=True).click()
    page.get_by_role('button', name='Show answer').click()
    expect(page.get_by_text('A thing')).to_be_visible()
    page.locator('header').get_by_role('link', name='Ask').click()
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_text('die Sache')).to_be_visible()
    expect(page.get_by_text('A thing')).to_be_visible()
    expect(page.get_by_role('button', name=re.compile('^Next'))).to_be_visible()


def test_read_article_can_be_resumed_after_add_and_ask(page, server):
    requests = []
    article = {'topic': 'physics', 'title': 'Ein neuer Rekord', 'publication': 'Publisher',
               'url': 'https://example.com/article', 'publishedAt': '2026-10-29', 'retrievedAt': '2026-10-30',
               'summary': 'Forscher melden einen Rekord.', 'words': ['Rekord']}
    page.route('**/api/read', lambda route: (requests.append(1), route.fulfill(json=article)))
    page.goto(server[0] + '/read?mode=url')
    page.get_by_label('Webpage URL').fill('https://www.zeit.de/example')
    page.get_by_role('button', name='Summarize webpage').click()
    expect(page.get_by_role('heading', name='Ein neuer Rekord')).to_be_visible()
    page.locator('header').get_by_role('link', name='Add').click()
    expect(page.get_by_role('link', name='Back to article')).to_be_visible()
    page.locator('header').get_by_role('link', name='Ask').click()
    page.get_by_role('link', name='Back to article').click()
    expect(page).to_have_url(re.compile(r'/read\?mode=url$'))
    expect(page.get_by_role('heading', name='Ein neuer Rekord')).to_be_visible()
    assert len(requests) == 1


def test_writing_returns_with_unsent_sentence(page, server):
    rounds = [[{'term': 'first', 'fileName': 'test', 'hint': 'one'}, {'term': 'second', 'fileName': 'test', 'hint': 'two'}]]
    page.route('**/api/writing', lambda route: route.fulfill(json={'source': 'test', 'rounds': rounds}))
    page.goto(server[0] + '/writing')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('textbox', name='Your sentence').fill('An unfinished sentence')
    page.locator('header').get_by_role('link', name='Ask').click()
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_role('textbox', name='Your sentence')).to_have_value('An unfinished sentence')
