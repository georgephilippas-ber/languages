from playwright.sync_api import expect


def test_device_dialog_enable_and_revoke(page, server):
    url, _ = server
    page.goto(url)
    page.get_by_role('button', name='Languages menu').click()
    page.get_by_role('menuitem', name='Other devices').click()
    dialog = page.get_by_role('dialog', name='Access from another device')
    expect(dialog).to_be_visible()
    dialog.get_by_role('button', name='Enable local access').click()
    expect(dialog.get_by_alt_text('QR code for local address')).to_be_visible()
    expect(dialog.get_by_role('button', name='Off', exact=True)).to_have_attribute('aria-pressed', 'true')
    dialog.get_by_role('button', name='3 hours', exact=True).click()
    expect(dialog.get_by_role('button', name='3 hours', exact=True)).to_have_attribute('aria-pressed', 'true')
    dialog.get_by_role('button', name='Off', exact=True).click()
    expect(dialog.get_by_role('button', name='Off', exact=True)).to_have_attribute('aria-pressed', 'true')
    dialog.get_by_role('button', name='Revoke local access').click()
    expect(dialog.get_by_role('button', name='Enable local access')).to_be_visible()
    expect(dialog.get_by_alt_text('QR code for local address')).to_have_count(0)


def test_local_and_internet_codes_are_separate(page, server):
    url, _ = server
    state = {'active': False}
    qr = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/%3E'
    def internet(route):
        if route.request.url.endswith('/start'):
            state['active'] = True
        elif route.request.url.endswith('/stop'):
            state['active'] = False
        route.fulfill(json={'installed': True, 'active': state['active'], 'starting': False,
                            'url': 'https://example.ngrok-free.app' if state['active'] else None,
                            'pin': '0421' if state['active'] else None, 'pinLocked': False,
                            'qr': qr, 'error': None})
    page.route('**/api/internet**', internet)
    page.goto(url)
    page.get_by_role('button', name='Languages menu').click()
    page.get_by_role('menuitem', name='Other devices').click()
    dialog = page.get_by_role('dialog', name='Access from another device')
    dialog.get_by_role('button', name='Enable local access').click()
    dialog.get_by_role('button', name='Enable internet access').click()
    local = dialog.get_by_alt_text('QR code for local address')
    remote = dialog.get_by_alt_text('QR code for internet access')
    expect(local).to_be_visible()
    expect(remote).to_be_visible()
    assert remote.bounding_box()['x'] > local.bounding_box()['x'] + local.bounding_box()['width']
    expect(dialog.get_by_text('0421')).to_be_visible()
    dialog.get_by_role('button', name='Stop internet access').click()
    expect(remote).to_have_count(0)
    expect(local).to_be_visible()


def test_keep_awake_button_updates_when_timer_expires(page, server):
    state = {'minutes': 0}
    def device(route):
        if '/awake/' in route.request.url:
            state['minutes'] = int(route.request.url.rsplit('/', 1)[-1])
        route.fulfill(json={'active': False, 'url': None, 'localUrl': None, 'awakeMinutes': state['minutes']})
    page.route('**/api/device**', device)
    page.goto(server[0])
    page.get_by_role('button', name='Languages menu').click()
    page.get_by_role('menuitem', name='Other devices').click()
    dialog = page.get_by_role('dialog', name='Access from another device')
    dialog.get_by_role('button', name='30 minutes').click()
    expect(dialog.get_by_role('button', name='30 minutes')).to_have_attribute('aria-pressed', 'true')
    state['minutes'] = 0  # The Mac's caffeinate process has ended.
    expect(dialog.get_by_role('button', name='Off', exact=True)).to_have_attribute('aria-pressed', 'true', timeout=6000)
    expect(dialog.get_by_role('button', name='30 minutes')).to_have_attribute('aria-pressed', 'false')
