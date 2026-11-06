import re
from playwright.sync_api import expect


def test_logo_menu_displays_sources_without_edit_controls(page, server):
    page.goto(server[0] + '/')
    page.get_by_role('button', name='Languages menu', exact=False).click()
    page.get_by_role('menuitem', name='Allowed sources').click()
    dialog = page.get_by_role('dialog', name='Allowed webpage sources')
    expect(dialog).to_be_visible()
    for name in ('English', 'German', 'French'):
        expect(dialog.get_by_role('heading', name=name)).to_be_visible()
    for domain in ('theguardian.com', 'cnn.com', 'ft.com', 'zeit.de', 'bild.de', 'lemonde.fr', 'lequipe.fr'):
        expect(dialog.get_by_text(domain, exact=True)).to_be_visible()
    assert dialog.locator('li').count() == 45
    assert dialog.get_by_role('link').count() == 45
    guardian = dialog.get_by_role('link', name='The Guardian theguardian.com')
    expect(guardian).to_have_attribute('href', 'https://theguardian.com')
    expect(guardian).to_have_attribute('target', '_blank')
    expect(dialog.get_by_role('textbox')).to_have_count(0)
    dialog.get_by_role('button', name='Close').click()
    expect(dialog).not_to_be_visible()


def test_header_sources_match_selected_language_and_open_new_tab(page, server):
    page.goto(server[0] + '/')
    header = page.locator('header')
    for width in (320, 390, 640, 768, 1024, 1280, 1440):
        page.set_viewport_size({'width': width, 'height': 800})
        assert header.evaluate('(el) => el.scrollWidth <= el.clientWidth')
        button = header.get_by_role('button', name='Sources')
        expect(button).to_be_visible()
        button.click()
        menu = header.get_by_role('menu', name=re.compile('sources$'))
        expect(menu.get_by_role('menuitem')).to_have_count(15)
        bounds = menu.bounding_box()
        assert bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= width
        page.keyboard.press('ArrowUp')
        expect(menu.get_by_role('menuitem').last).to_be_focused()
        page.keyboard.press('Escape')
    for code, language, expected, excluded in [('EN', 'English', 'The Economist', 'Die Zeit'),
                                                ('DE', 'German', 'Die Zeit', 'The Economist'),
                                                ('FR', 'French', 'Le Monde', 'Die Zeit')]:
        header.get_by_role('button', name=code, exact=True).click()
        button = header.get_by_role('button', name='Sources')
        button.click()
        menu = header.get_by_role('menu', name=f'{language} sources')
        expect(menu).to_be_visible()
        expect(menu.get_by_role('menuitem')).to_have_count(15)
        link = menu.get_by_role('menuitem', name=expected, exact=True)
        expect(link).to_be_visible()
        expect(link).to_have_attribute('target', '_blank')
        expect(link).to_have_attribute('href', re.compile(r'^https://'))
        expect(menu.get_by_role('menuitem', name=excluded, exact=True)).to_have_count(0)
        page.keyboard.press('Escape')
        expect(menu).to_have_count(0)
        expect(button).to_be_focused()
