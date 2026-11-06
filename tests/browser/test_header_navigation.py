import re
from playwright.sync_api import expect


def test_exercises_are_available_from_home_without_header_links(page, server):
    page.goto(server[0] + '/')
    for width in (320, 390, 768, 1024, 1440):
        page.set_viewport_size({'width': width, 'height': 800})
        assert page.locator('header').evaluate('(header) => header.scrollWidth <= header.clientWidth')
        expect(page.get_by_role('navigation', name='Exercises')).to_have_count(0)
        expect(page.get_by_role('group', name='Language')).to_be_visible()
    for title in ('Recognise', 'Produce', 'Use', 'Connect', 'Agree'):
        expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
    for title in ('Read', 'Translate', 'Review', 'Add', 'Ask'):
        expect(page.get_by_role('button', name=re.compile('^' + title))).to_be_visible()
    page.get_by_role('button', name=re.compile('^Translate')).click()
    expect(page.get_by_role('heading', name='Translate', exact=True)).to_be_visible()
    page.get_by_role('button', name=re.compile('^Languages menu')).click()
    page.get_by_role('menuitem', name='Home').click()
    expect(page.get_by_role('heading', name=re.compile('Your words'))).to_be_visible()
