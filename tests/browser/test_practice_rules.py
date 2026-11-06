import re
from playwright.sync_api import expect


def test_practice_rules_open_from_menu_and_close_with_escape(page, server):
    page.goto(server[0] + '/')
    page.locator('header').get_by_role('button', name=re.compile('^Languages menu')).click()
    menu = page.get_by_role('menu', name='Languages')
    expect(menu.get_by_role('menuitem').last).to_have_text('Exit')
    expect(menu.get_by_role('menuitem').nth(-2)).to_have_text('Settings')
    expect(menu.locator('[role=separator] + [role=menuitem]')).to_have_text(['Other devices', 'Settings'])
    expect(menu.get_by_role('menuitem').nth(-3)).to_contain_text('Other devices')
    page.get_by_role('menuitem', name='Earning credits').click()
    dialog = page.get_by_role('dialog', name='Earning credits')
    expect(dialog).to_be_visible()
    for text in ('10 credits', 'Every five correct', 'Phrasal verbs do not spend or earn', 'due after 6 hours'):
        expect(dialog.get_by_text(text, exact=False)).to_be_visible()
    page.keyboard.press('Escape')
    expect(dialog).not_to_be_visible()
