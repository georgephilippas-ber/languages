import re

from playwright.sync_api import expect


def test_produce_hints_reveal_progress_and_resume(page, server):
    url, _ = server
    words = ['banana', 'abcdefgh', 'aa']
    page.route('**/api/typed', lambda route: route.fulfill(json={
        'source': 'synthetic', 'questions': [
            {'term': word, 'question': 'The answer is _____.', 'hint': 'A meaning', 'correctAnswer': word,
             'completeSentence': f'The answer is {word}.', 'englishTranslation': 'A sentence.'}
            for word in words]}))
    page.route('**/api/typed/check', lambda route: route.fulfill(json={
        'verdict': 'correct', 'correctedAnswer': route.request.post_data_json['answer'], 'errors': [],
        'comment': '', 'suggestions': [], 'notice': None}))
    page.goto(url + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    button = page.get_by_role('button', name=re.compile(r'^Reveal letter'))
    hint = page.locator('[aria-label="Revealed letters"]')
    expect(button).to_contain_text('0/3')
    expect(hint).to_be_hidden()
    check = page.get_by_role('button', name=re.compile(r'^Check'))
    original_y = check.bounding_box()['y']
    button.click()
    expect(hint).to_have_text('b•••••')
    assert abs(check.bounding_box()['y'] - original_y) < 1
    expect(page.get_by_role('textbox', name='Your answer')).to_be_focused()
    page.evaluate('Math.random = () => 0')
    button.click()
    expect(hint).to_have_text('ba•a•a')
    assert abs(check.bounding_box()['y'] - original_y) < 1
    expect(button).to_contain_text('2/3')
    page.reload()
    page.get_by_role('button', name='Resume', exact=True).click()
    expect(hint).to_have_text('ba•a•a')
    expect(button).to_contain_text('2/3')
    page.evaluate('Math.random = () => 0')
    button.click()
    expect(hint).to_have_text('banana')
    expect(button).to_be_disabled()
    page.get_by_role('textbox', name='Your answer').fill('banana')
    page.get_by_role('button', name=re.compile(r'^Check')).click()
    page.get_by_role('button', name=re.compile(r'^Next')).click()
    expect(button).to_contain_text('0/3')
    expect(hint).to_be_hidden()
    for _ in range(3):
        button.click()
    expect(hint).to_have_text('abc•••••')
    expect(button).to_be_disabled()
    page.get_by_role('textbox', name='Your answer').fill('abcdefgh')
    page.get_by_role('button', name=re.compile(r'^Check')).click()
    page.get_by_role('button', name=re.compile(r'^Next')).click()
    button.click()
    expect(hint).to_have_text('a•')
    button.click()
    expect(hint).to_have_text('aa')
    expect(button).to_be_disabled()


def test_hint_is_limited_to_produce(page, server):
    url, _ = server
    page.route('**/api/prepositions', lambda route: route.fulfill(json={
        'source': 'synthetic', 'questions': [
            {'term': 'sich befassen', 'question': 'Ich befasse mich _____ dem Thema.', 'hint': 'deal with',
             'correctAnswer': 'mit', 'completeSentence': 'Ich befasse mich mit dem Thema.',
             'englishTranslation': 'I deal with the topic.'}]}))
    page.goto(url + '/prepositions')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    expect(page.get_by_role('textbox', name='Missing preposition')).to_be_visible()
    expect(page.get_by_role('button', name=re.compile(r'^Reveal letter'))).to_have_count(0)


def test_hints_preserve_accents_case_and_punctuation(page, server):
    url, _ = server
    answer = 'Été d’été'
    page.route('**/api/typed', lambda route: route.fulfill(json={
        'source': 'synthetic', 'questions': [
            {'term': answer, 'question': 'The answer is _____.', 'hint': 'A meaning', 'correctAnswer': answer,
             'completeSentence': f'The answer is {answer}.', 'englishTranslation': 'A sentence.'}]}))
    page.goto(url + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    button = page.get_by_role('button', name=re.compile(r'^Reveal letter'))
    hint = page.locator('[aria-label="Revealed letters"]')
    button.click()
    expect(hint).to_have_text('É•• •’•••')
    page.evaluate('Math.random = () => 0.5')
    button.click()
    expect(hint).to_have_text('É•é •’é•é')
    page.evaluate('Math.random = () => 0.999')
    button.click()
    expect(hint).to_have_text('É•é d’é•é')
    expect(button).to_be_disabled()


def test_revealing_a_wrapped_answer_does_not_move_controls(page, server):
    url, _ = server
    answer = 'supercalifragilisticexpialidocious and something else'
    page.set_viewport_size({'width': 360, 'height': 800})
    page.route('**/api/typed', lambda route: route.fulfill(json={
        'source': 'synthetic', 'questions': [
            {'term': answer, 'question': 'Here is _____.', 'hint': 'A meaning', 'correctAnswer': answer,
             'completeSentence': f'Here is {answer}.', 'englishTranslation': 'A sentence.'}]}))
    page.goto(url + '/typed')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    reveal = page.get_by_role('button', name=re.compile(r'^Reveal letter'))
    check = page.get_by_role('button', name=re.compile(r'^Check'))
    expect(reveal).to_be_visible()
    position = lambda: check.evaluate('(element) => element.getBoundingClientRect().top + window.scrollY')
    before = position()
    for _ in range(3):
        reveal.click()
        assert abs(position() - before) < 1
