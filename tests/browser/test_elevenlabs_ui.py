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
    expect(page.get_by_role('menuitem', name='Set OpenAI API key')).to_contain_text('WXYZ')
    page.get_by_role('menuitem', name='Set ElevenLabs API key').click()
    expect(page.get_by_role('heading', name='ElevenLabs API key')).to_be_visible()
    page.get_by_label('New ElevenLabs API key').fill('sk_test_01234567891234')
    page.get_by_role('button', name='Save key').click()
    expect(page.get_by_role('heading', name='ElevenLabs API key')).to_have_count(0)
    assert saved == [('elevenlabs', 'sk_test_01234567891234')]
    page.get_by_role('button', name=re.compile('^Languages menu')).click()
    expect(page.get_by_role('menuitem', name='Set ElevenLabs API key')).to_contain_text('1234')
    expect(page.get_by_role('menuitem', name='Set OpenAI API key')).to_contain_text('WXYZ')
