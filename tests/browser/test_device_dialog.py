from playwright.sync_api import expect


def test_device_dialog_enable_and_revoke(page, server):
    url, _ = server
    page.goto(url)
    page.get_by_role('button', name='Languages menu').click()
    page.get_by_role('menuitem', name='Other devices').click()
    dialog = page.get_by_role('dialog', name='Access from another device')
    expect(dialog).to_be_visible()
    dialog.get_by_role('button', name='Enable access').click()
    expect(dialog.get_by_alt_text('QR code for device access')).to_be_visible(timeout=10000)
    expect(dialog.get_by_alt_text('QR code for local address')).to_be_visible()
    expect(dialog.get_by_role('button', name='Off', exact=True)).to_have_attribute('aria-pressed', 'true')
    dialog.get_by_role('button', name='3 hours', exact=True).click()
    expect(dialog.get_by_role('button', name='3 hours', exact=True)).to_have_attribute('aria-pressed', 'true')
    dialog.get_by_role('button', name='Off', exact=True).click()
    expect(dialog.get_by_role('button', name='Off', exact=True)).to_have_attribute('aria-pressed', 'true')
    dialog.get_by_role('button', name='Revoke access').click()
    expect(dialog.get_by_role('button', name='Enable access')).to_be_visible()
    expect(dialog.get_by_alt_text('QR code for device access')).to_have_count(0)
    expect(dialog.get_by_alt_text('QR code for local address')).to_have_count(0)
