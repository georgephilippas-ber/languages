import re
from playwright.sync_api import expect


def test_independent_keys_can_be_set_from_logo_menu(page, server):
    status = {'openai': {'configured': True, 'hint': 'WXYZ', 'source': 'file'},
              'elevenlabs': {'configured': False, 'hint': None, 'source': None}}
    saved = []
    def endpoint(route):
        provider = 'elevenlabs' if 'elevenlabs-key' in route.request.url else 'openai'
        if route.request.method == 'PUT':
            saved.append((provider, route.request.post_data_json['key']))
            status[provider] = {'configured': True, 'hint': route.request.post_data_json['key'][-4:], 'source': 'file'}
        route.fulfill(json=status[provider])
    page.route('**/api/settings/api-key', endpoint)
    page.route('**/api/settings/elevenlabs-key', endpoint)
    page.goto(server[0] + '/')
    page.get_by_role('button', name=re.compile('^Languages menu')).click()
    page.get_by_role('menuitem', name='Settings').click()
    dialog = page.get_by_role('dialog', name='Settings')
    expect(dialog.get_by_text('Key ending in …WXYZ is in use.')).to_be_visible()
    expect(dialog.get_by_role('heading', name='ElevenLabs')).to_be_visible()
    for name, url in [('OpenAI', 'https://platform.openai.com/api-keys'), ('ElevenLabs', 'https://elevenlabs.io/app/api/api-keys')]:
        link = dialog.get_by_role('link', name=name, exact=True)
        expect(link).to_have_attribute('href', url)
        expect(link).to_have_attribute('target', '_blank')
    dialog.get_by_label('New ElevenLabs API key').fill('sk_test_01234567891234')
    dialog.get_by_role('button', name='Save ElevenLabs key').click()
    expect(dialog.get_by_text('ElevenLabs key saved')).to_be_visible()
    expect(dialog.get_by_text('Key ending in …1234 is in use.')).to_be_visible()
    expect(dialog.get_by_text('Key ending in …WXYZ is in use.')).to_be_visible()
    assert saved == [('elevenlabs', 'sk_test_01234567891234')]
    dialog.get_by_label('New OpenAI API key').fill('sk-new-openai-5678')
    dialog.get_by_role('button', name='Save OpenAI key').click()
    expect(dialog.get_by_text('OpenAI key saved')).to_be_visible()
    expect(dialog.get_by_text('Key ending in …1234 is in use.')).to_be_visible()
    assert saved[-1] == ('openai', 'sk-new-openai-5678')
    dialog.get_by_role('button', name='Close').click()
    expect(dialog).not_to_be_visible()
