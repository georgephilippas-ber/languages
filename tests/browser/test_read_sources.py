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
    expect(dialog.get_by_role('textbox')).to_have_count(0)
    dialog.get_by_role('button', name='Close').click()
    expect(dialog).not_to_be_visible()
