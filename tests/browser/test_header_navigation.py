import re
from playwright.sync_api import expect


def test_exercises_are_available_from_home_without_header_links(page, server):
    page.goto(server[0] + '/')
    for width in (320, 390, 768, 1024, 1440):
        page.set_viewport_size({'width': width, 'height': 800})
        assert page.locator('header').evaluate('(header) => header.scrollWidth <= header.clientWidth')
        expect(page.get_by_role('navigation', name='Exercises')).to_have_count(0)
        expect(page.get_by_role('group', name='Language')).to_be_visible()
        expect(page.locator('header').get_by_role('link', name='Read')).to_be_visible()
        expect(page.locator('header').get_by_role('button', name='I feel lucky')).to_be_visible()
    for title in ('Recognise', 'Produce', 'Use', 'Connect', 'Agree'):
        expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
    for title in ('Read', 'Translate', 'Review', 'Add', 'Ask'):
        expect(page.get_by_role('button', name=re.compile('^' + title))).to_be_visible()
    page.get_by_role('button', name=re.compile('^Translate')).click()
    expect(page.get_by_role('heading', name='Translate', exact=True)).to_be_visible()
    page.get_by_role('button', name=re.compile('^Languages menu')).click()
    page.get_by_role('menuitem', name='Home').click()
    expect(page.get_by_role('heading', name=re.compile('Your words'))).to_be_visible()


def test_home_and_back_links_return_to_expected_pages(page, server):
    url = server[0]
    page.set_viewport_size({'width': 320, 'height': 800})
    page.goto(url + '/typed')
    header = page.locator('header')
    assert header.evaluate('(e) => e.scrollWidth <= e.clientWidth')
    expect(header.get_by_role('link', name='Home')).to_be_visible()
    page.get_by_role('link', name='Back', exact=True).click()
    expect(page.get_by_role('heading', name=re.compile('Your words'))).to_be_visible()
    page.goto(url + '/translate/produce')
    page.get_by_role('link', name='Back', exact=True).click()
    expect(page.get_by_role('heading', name='Translate', exact=True)).to_be_visible()
    page.get_by_role('link', name='Back', exact=True).click()
    expect(page.get_by_role('heading', name=re.compile('Your words'))).to_be_visible()
    page.goto(url + '/review')
    expect(page.get_by_role('link', name='Back', exact=True)).to_be_visible()
    header.get_by_role('link', name='Home').click()
    expect(page.get_by_role('heading', name=re.compile('Your words'))).to_be_visible()


def test_exercise_toolbar_stays_below_wrapping_header(page, server):
    question = {'term': 'one', 'question': 'This is _____.', 'choices': ['one', 'two'], 'correctChoice': 0,
                'completeSentence': 'This is one.', 'englishTranslation': 'One thing.', 'choicesTranslations': []}
    page.route('**/api/quiz', lambda route: route.fulfill(json={'source': 'test', 'questions': [question]}))
    page.set_viewport_size({'width': 320, 'height': 800})
    page.goto(server[0] + '/quiz')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    progress = page.get_by_role('progressbar')
    expect(progress).to_be_visible()
    page.wait_for_function('''() => {
      const header = document.querySelector('header');
      const toolbar = document.querySelector('[role="progressbar"]')?.closest('.sticky');
      return header && toolbar && parseFloat(getComputedStyle(toolbar).top) >= header.offsetHeight;
    }''')
