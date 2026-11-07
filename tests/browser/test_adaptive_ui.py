import re
from playwright.sync_api import expect


def test_word_credit_shows_low_warning_on_home_and_add(page, server):
    page.route('**/api/entries/allowance?*', lambda route: route.fulfill(json={'available': 3, 'reviews_toward_next': 2}))
    page.goto(server[0] + '/')
    expect(page.get_by_role('status').filter(has_text='Low word credit')).to_contain_text('Word credit: 3')
    page.locator('header').get_by_role('link', name='Add', exact=True).click()
    expect(page.get_by_role('status').filter(has_text='Low word credit')).to_contain_text('Word credit: 3')
    expect(page.get_by_text('3 successful reviews until the next word')).to_be_visible()


def test_seen_and_answered_are_recorded_separately(page, server):
    requests = []
    question = {'term':'test word', 'question':'This is _____.', 'choices':['one','two','three','four'], 'correctChoice':0, 'completeSentence':'This is one.', 'englishTranslation':'One.', 'choicesTranslations':[]}
    page.route('**/api/quiz', lambda route: route.fulfill(json={'source':'test','questions':[question]}))
    page.route('**/api/exercise-progress', lambda route: (requests.append(route.request.post_data_json), route.fulfill(status=204)))
    page.goto(server[0] + '/quiz')
    page.get_by_role('button', name=re.compile('^Start')).click()
    expect(page.get_by_text('This is', exact=False).first).to_be_visible()
    page.get_by_role('button', name=re.compile('one')).first.click()
    page.wait_for_function('() => document.querySelector("[aria-label=\\"1 of 1 answered\\"]") !== null')
    page.wait_for_timeout(250)
    assert [event['answers'][0]['outcome'] for event in requests] == ['seen', 'correct']
    assert all(event['skill'] == 'recognize' for event in requests)


def test_queue_displays_newest_first_and_keeps_excess_entries(page, server):
    page.route('**/api/entries/allowance?*', lambda route: route.fulfill(json={'available': -4, 'reviews_toward_next': 0}))
    page.goto(server[0] + '/')
    page.evaluate('''() => localStorage.setItem('languages.drafts', JSON.stringify([
      {id:'old',language:'DE',request:'older',term:'older',status:'ready',markdown:'## older\\n\\n**Definition:** old.'},
      {id:'new',language:'DE',request:'newer',term:'newer',status:'ready',markdown:'## newer\\n\\n**Definition:** new.'}
    ]))''')
    saved = []
    def save(route):
        saved.extend(route.request.post_data_json['entries'])
        route.fulfill(json={'saved':[{'term':'older', 'fileName':'german-1.md', 'termsInFile':13}], 'fileName':'german-1.md', 'termsInFile':13, 'fileFull':False})
    page.route('**/api/entries/save', save)
    page.goto(server[0] + '/add')
    headings = page.locator('article h3')
    expect(headings).to_have_text(['newer', 'older'])
    page.get_by_role('button', name='Add 1 entry').click()
    expect(headings).to_have_text(['newer'])
    assert len(saved) == 1 and saved[0].startswith('## older')


def test_phrasal_verb_can_be_saved_when_english_credit_is_zero(page, server):
    page.route('**/api/entries/allowance?*', lambda route: route.fulfill(json={'available': -5, 'reviews_toward_next': 0}))
    page.goto(server[0] + '/')
    page.locator('header').get_by_role('button', name='EN', exact=True).click()
    page.evaluate('''() => localStorage.setItem('languages.drafts', JSON.stringify([
      {id:'x',language:'EN',request:'to set forth',term:'to set forth',status:'ready',category:'phrasal-verbs',markdown:'## to set forth\\n\\n**Definition:** explain.'},
      {id:'y',language:'EN',request:'general',term:'general',status:'ready',category:'general',markdown:'## general\\n\\n**Definition:** general.'}
    ]))''')
    saved = []
    def save(route):
        saved.append(route.request.post_data_json)
        route.fulfill(json={'saved':[{'term':'to set forth', 'fileName':'english-phrasal-verbs-1.md', 'termsInFile':1}], 'fileName':'english-phrasal-verbs-1.md', 'termsInFile':1, 'fileFull':False})
    page.route('**/api/entries/save', save)
    page.goto(server[0] + '/add')
    page.get_by_role('button', name='Add 1 entry').click()
    expect(page.locator('article h3')).to_have_text(['general'])
    assert saved[0]['category'] == 'phrasal-verbs'
