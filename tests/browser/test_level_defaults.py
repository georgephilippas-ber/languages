from playwright.sync_api import expect


def test_c1_default_in_each_language_and_exercise(page, server):
    url, _ = server
    for language in ('DE', 'FR', 'EN'):
        page.goto(url + '/')
        page.get_by_role('button', name=language, exact=True).click()
        paths = ['/quiz', '/typed', '/writing', '/prepositions', '/read']
        if language != 'EN':
            paths.append('/articles')
        for path in paths:
            page.goto(url + path)
            levels = page.get_by_role('group', name='CEFR level')
            expect(levels.get_by_role('button', name='C1', exact=True)).to_have_attribute('aria-pressed', 'true')


def test_explicit_level_choice_is_remembered(page, server):
    url, _ = server
    page.goto(url + '/typed')
    levels = page.get_by_role('group', name='CEFR level')
    levels.get_by_role('button', name='B1', exact=True).click()
    page.reload()
    expect(levels.get_by_role('button', name='B1', exact=True)).to_have_attribute('aria-pressed', 'true')
