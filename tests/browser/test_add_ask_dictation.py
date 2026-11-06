import re
from playwright.sync_api import expect
from test_use_dictation import MOCK_RECORDER


def test_add_dictation_appends_one_editable_line_and_shows_usage(page, server):
    page.add_init_script(MOCK_RECORDER)
    calls = []
    defines = []
    page.route('**/api/transcribe?*', lambda route: (calls.append(route.request.url), route.fulfill(json={'text': 'die Krähe.', 'usage': {'credits': 3, 'audioSeconds': 2.5}})))
    page.route('**/api/entries/define', lambda route: (defines.append(1), route.fulfill(json={'term': 'test', 'markdown': '## test\n\n**Definition:** A term.', 'gloss': 'test'})))
    page.goto(server[0] + '/add')
    text = page.get_by_role('textbox', name='German vocabulary, one per line')
    text.fill('die Sache')
    page.get_by_role('button', name='Speak a word or sentence').click()
    expect(page.get_by_role('button', name='Write entries')).to_be_disabled()
    page.get_by_role('button', name='Stop and transcribe').click()
    expect(text).to_have_value('die Sache\ndie Krähe.')
    expect(page.get_by_role('status').filter(has_text='Last transcription')).to_contain_text('3 credits')
    expect(page.get_by_role('status').filter(has_text='Last transcription')).to_contain_text('2.5 seconds')
    assert len(calls) == 1 and 'language=DE' in calls[0] and not defines
    expect(page.get_by_role('button', name='Write entries')).to_be_enabled()


def test_ask_dictation_language_and_no_automatic_submission(page, server):
    page.add_init_script(MOCK_RECORDER)
    calls, asks = [], []
    page.route('**/api/transcribe?*', lambda route: (calls.append(route.request.url), route.fulfill(json={'text': 'une question', 'usage': {'credits': 1}})))
    page.route('**/api/ask', lambda route: (asks.append(1), route.fulfill(json={'answer': 'answer', 'onTopic': True})))
    page.goto(server[0] + '/ask')
    page.get_by_label('Spoken language').select_option('FR')
    text = page.get_by_role('textbox', name='Your question')
    text.fill('Bonjour')
    page.get_by_role('button', name='Speak question').click()
    expect(page.get_by_label('Spoken language')).to_be_disabled()
    expect(page.locator('main').get_by_role('button', name=re.compile('^Ask'))).to_be_disabled()
    page.get_by_role('button', name='Stop and transcribe').click()
    expect(text).to_have_value('Bonjour une question')
    expect(page.get_by_role('status').filter(has_text='Last transcription')).to_contain_text('1 credit')
    assert 'language=FR' in calls[0] and not asks
    text.fill('x' * 1990)
    page.get_by_role('button', name='Speak question').click()
    page.get_by_role('button', name='Stop and transcribe').click()
    expect(page.get_by_role('alert')).to_contain_text('Please shorten')
    expect(page.locator('main').get_by_role('button', name=re.compile('^Ask'))).to_be_disabled()


def test_empty_transcription_still_shows_reported_usage(page, server):
    page.add_init_script(MOCK_RECORDER)
    page.route('**/api/transcribe?*', lambda route: route.fulfill(json={'text': '', 'usage': {'credits': 1, 'audioSeconds': 0.5}}))
    page.goto(server[0] + '/add')
    page.get_by_role('button', name='Speak a word or sentence').click()
    page.get_by_role('button', name='Stop and transcribe').click()
    expect(page.get_by_role('alert')).to_contain_text('No speech was recognized')
    expect(page.get_by_role('status').filter(has_text='Last transcription')).to_contain_text('1 credit')
