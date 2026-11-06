import re
from playwright.sync_api import expect

QUESTION = {'sourceLanguage': 'DE', 'targetLanguage': 'EN', 'sourceSentence': 'Die Katze sieht den Hund.',
            'segments': ['The ', ' sees the ', '.'], 'answers': ['cat', 'dog'], 'hint': 'Two animals',
            'choices': [['cat', 'dog'], ['cat', 'bird'], ['dog', 'cat'], ['bird', 'dog']],
            'correctChoice': 0, 'terms': ['die Katze', 'der Hund']}


def test_mixed_recognize_navigation_and_two_blanks(page, server):
    url, _ = server
    requests = []
    def generate(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json={'source': 'English, German and French vocabulary', 'questions': [QUESTION]})
    page.route('**/api/mixed-translation', generate)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(url + '/')
    for width in (390, 768, 1024, 1280, 1440):
        page.set_viewport_size({'width': width, 'height': 844})
        assert page.locator('header').evaluate('(e) => e.scrollWidth <= e.clientWidth')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.get_by_role('button', name=re.compile('^Translate')).click()
    page.get_by_role('link', name=re.compile('Recognize')).click()
    expect(page.get_by_text('All English, German and French vocabulary')).to_be_visible()
    checkbox = page.get_by_role('checkbox', name='Include English phrasal verbs')
    expect(checkbox).not_to_be_checked()
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    expect(page.get_by_text('Die Katze sieht den Hund.')).to_be_visible()
    expect(page.get_by_text('English translation', exact=True)).to_be_visible()
    expect(page.get_by_role('img', name=re.compile('Blank'))).to_have_count(2)
    assert requests[0]['mode'] == 'recognize' and requests[0]['includePhrasal'] is False
    page.keyboard.press('1')
    expect(page.get_by_text('Correct', exact=True).first).to_be_visible()
    expect(page.get_by_role('region', name='Feedback').get_by_text('The cat sees the dog.', exact=True)).to_be_visible()


def test_mixed_produce_keyboard_and_two_answers(page, server):
    url, _ = server
    requests = []
    page.route('**/api/mixed-translation', lambda route: (requests.append(route.request.post_data_json), route.fulfill(json={'source': 'Mixed vocabulary', 'questions': [QUESTION]})))
    page.route('**/api/mixed-translation/check', lambda route: route.fulfill(json={'verdict': 'correct', 'correctedAnswers': ['cat', 'dog'], 'comment': ''}))
    page.goto(url + '/translate/produce')
    page.get_by_role('checkbox', name='Include English phrasal verbs').check()
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    assert requests[0]['mode'] == 'produce' and requests[0]['includePhrasal'] is True
    first = page.get_by_role('textbox', name='Translation blank 1')
    second = page.get_by_role('textbox', name='Translation blank 2')
    expect(first).to_be_visible(); expect(second).to_be_visible()
    page.keyboard.press('Control+h')
    expect(page.get_by_text('Two animals')).to_be_visible()
    page.keyboard.press('Control+l')
    expect(page.locator('[aria-label="Revealed letters"]')).to_have_text('c•• / •••')
    first.fill('cat'); second.fill('dog')
    page.get_by_role('button', name=re.compile('^Check')).click()
    expect(page.get_by_text('Correct', exact=True).first).to_be_visible()
    expect(page.get_by_role('region', name='Feedback').get_by_text('The cat sees the dog.', exact=True)).to_be_visible()
