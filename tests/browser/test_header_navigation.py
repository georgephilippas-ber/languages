import re
from playwright.sync_api import expect


def test_exercises_are_available_from_home_without_header_links(page, server):
    page.goto(server[0] + '/')
    for width in (320, 390, 640, 768, 1024, 1440):
        page.set_viewport_size({'width': width, 'height': 800})
        assert page.locator('header').evaluate('(header) => header.scrollWidth <= header.clientWidth')
        expect(page.get_by_role('navigation', name='Exercises')).to_have_count(0)
        expect(page.get_by_role('group', name='Language')).to_be_visible()
        expect(page.locator('header').get_by_role('button', name='Read')).to_be_visible()
        expect(page.locator('header').get_by_role('link', name='Add')).to_be_visible()
        expect(page.locator('header').get_by_role('link', name='Ask')).to_be_visible()
        expect(page.locator('header').get_by_role('button', name='I feel lucky')).to_be_visible()
        expect(page.locator('header').get_by_role('button', name='I feel lucky')).to_have_class(re.compile('bg-accent-soft'))
        expect(page.locator('main').get_by_role('button', name='I feel lucky')).to_have_count(0)
    for title in ('Recognise', 'Produce', 'Use', 'Connect', 'Agree'):
        expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
    for title in ('Read', 'Translate', 'Review', 'Add', 'Ask'):
        expect(page.locator('main').get_by_role('button', name=re.compile('^' + title))).to_be_visible()
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


def test_app_icon_and_name_open_separate_menus(page, server):
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(server[0] + '/')
    header = page.locator('header')
    app_menu = header.get_by_role('button', name=re.compile('^Languages menu'))
    exercises_button = header.get_by_role('button', name='Exercises menu')
    expect(app_menu).to_be_visible()
    expect(exercises_button).to_be_visible()
    app_menu.click()
    expect(page.get_by_role('menu', name='Languages')).to_be_visible()
    expect(page.get_by_role('menuitem', name='API keys')).to_be_visible()
    exercises_button.click()
    expect(page.get_by_role('menu', name='Languages')).not_to_be_visible()
    menu = page.get_by_role('menu', name='Exercises', exact=True)
    expect(menu).to_be_visible()
    expect(menu.get_by_role('separator')).to_have_count(3)
    for name in ('Recognise · Multiple choice', 'Produce · Typed quiz', 'Use · Writing', 'Connect · Prepositions', 'Agree · Articles', 'Recognize translation', 'Produce translation', 'Review'):
        expect(menu.get_by_role('menuitem', name=name, exact=True)).to_be_visible()
    page.keyboard.press('End')
    expect(menu.get_by_role('menuitem', name='Review')).to_be_focused()
    page.keyboard.press('Home')
    expect(menu.get_by_role('menuitem', name=re.compile('^Recognise'))).to_be_focused()
    page.keyboard.press('Escape')
    expect(menu).not_to_be_visible()
    expect(exercises_button).to_be_focused()
    header.get_by_role('button', name='EN', exact=True).click()
    exercises_button.click()
    expect(menu.get_by_role('menuitem', name=re.compile('^Agree'))).to_have_count(0)
    menu.get_by_role('menuitem', name='Produce translation').click()
    expect(page).to_have_url(re.compile('/translate/produce$'))


def test_main_navigation_is_centered_in_available_space(page, server):
    page.set_viewport_size({'width': 1440, 'height': 800})
    page.goto(server[0] + '/')
    nav = page.get_by_role('navigation', name='Main navigation')
    expect(nav).to_be_visible()
    bounds = nav.bounding_box()
    first = nav.get_by_role('link', name='Home').bounding_box()
    last = nav.get_by_role('link', name='Ask').bounding_box()
    content_center = (first['x'] + last['x'] + last['width']) / 2
    available_center = bounds['x'] + bounds['width'] / 2
    assert abs(content_center - available_center) < 2
    for width in (320, 390, 640, 768, 1024, 1280):
        page.set_viewport_size({'width': width, 'height': 800})
        assert page.locator('header').evaluate('(el) => el.scrollWidth <= el.clientWidth')
        for name in ('Home', 'Add', 'Ask'):
            expect(nav.get_by_role('link', name=name)).to_be_visible()
        expect(nav.get_by_role('button', name='Read')).to_be_visible()
        expect(nav.get_by_role('button', name='I feel lucky')).to_be_visible()
