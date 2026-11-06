import re
from playwright.sync_api import expect


MOCK_RECORDER = '''
  window.stoppedTracks = 0;
  const track = {stop: () => window.stoppedTracks++};
  Object.defineProperty(navigator, 'mediaDevices', {configurable: true, value: {getUserMedia: async () => ({getTracks: () => [track]})}});
  window.MediaRecorder = class {
    static isTypeSupported(type) { return type.startsWith('audio/webm') }
    constructor(stream, options) { this.state = 'inactive'; this.mimeType = options?.mimeType || 'audio/webm'; }
    start() { this.state = 'recording' }
    stop() { this.state = 'inactive'; setTimeout(() => {
      this.ondataavailable?.({data: new Blob(['test audio'], {type: 'audio/webm'})}); this.onstop?.();
    }, 0) }
  };
'''


def setup_writing(page, server):
    page.route('**/api/writing', lambda route: route.fulfill(json={'source': 'test', 'rounds': [[
        {'term': 'first', 'fileName': 'test', 'hint': 'one'}, {'term': 'second', 'fileName': 'test', 'hint': 'two'}]]}))
    page.goto(server[0] + '/writing')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    expect(page.get_by_role('textbox', name='Your sentence')).to_be_visible()


def test_dictation_appends_editable_text_and_preserves_exercise(page, server):
    page.add_init_script(MOCK_RECORDER)
    calls = []
    def transcribe(route):
        calls.append((route.request.url, route.request.header_value('content-type'), route.request.post_data_buffer))
        route.fulfill(json={'text': 'ein gesprochener Satz.'})
    page.route('**/api/transcribe?*', transcribe)
    setup_writing(page, server)
    text = page.get_by_role('textbox', name='Your sentence')
    text.fill('Schon geschrieben.')
    page.get_by_role('button', name='Speak sentence').click()
    expect(page.get_by_role('button', name='Stop and transcribe')).to_be_visible()
    expect(page.get_by_role('button', name=re.compile('^Check'))).to_be_disabled()
    page.get_by_role('button', name='Stop and transcribe').click()
    expect(text).to_have_value('Schon geschrieben. ein gesprochener Satz.')
    expect(page.get_by_role('button', name=re.compile('^Check'))).to_be_enabled()
    assert len(calls) == 1 and 'language=DE' in calls[0][0] and calls[0][1] == 'audio/webm'
    assert calls[0][2] == b'test audio' and page.evaluate('window.stoppedTracks') == 1
    text.fill('Edited sentence')
    page.locator('header').get_by_role('link', name='Add').click()
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_role('textbox', name='Your sentence')).to_have_value('Edited sentence')


def test_cancel_recording_does_not_send_audio(page, server):
    page.add_init_script(MOCK_RECORDER)
    calls = []
    page.route('**/api/transcribe?*', lambda route: (calls.append(1), route.fulfill(json={'text': 'unexpected'})))
    setup_writing(page, server)
    page.get_by_role('button', name='Speak sentence').click()
    expect(page.get_by_role('button', name='Stop and transcribe')).to_be_visible()
    page.get_by_role('button', name='Cancel', exact=True).click()
    expect(page.get_by_role('button', name='Speak sentence')).to_be_visible()
    page.wait_for_timeout(100)
    assert not calls and page.evaluate('window.stoppedTracks') == 1


def test_permission_error_keeps_typing_available(page, server):
    page.add_init_script('''Object.defineProperty(navigator, 'mediaDevices', {configurable:true, value:{getUserMedia: async () => {throw new DOMException('denied', 'NotAllowedError')}}});''')
    setup_writing(page, server)
    page.get_by_role('button', name='Speak sentence').click()
    expect(page.get_by_role('alert')).to_contain_text('Microphone permission was denied')
    page.get_by_role('textbox', name='Your sentence').fill('Still able to type')
    expect(page.get_by_role('button', name=re.compile('^Check'))).to_be_enabled()


def test_starting_new_recording_after_cancel_is_not_stopped_by_old_event(page, server):
    page.add_init_script(MOCK_RECORDER)
    calls = []
    page.route('**/api/transcribe?*', lambda route: (calls.append(1), route.fulfill(json={'text': 'A sentence.'})))
    setup_writing(page, server)
    page.get_by_role('button', name='Speak sentence').click()
    expect(page.get_by_role('button', name='Stop and transcribe')).to_be_visible()
    page.get_by_role('button', name='Cancel', exact=True).click()
    page.get_by_role('button', name='Speak sentence').click()
    expect(page.get_by_role('button', name='Stop and transcribe')).to_be_visible()
    page.wait_for_timeout(100)
    page.get_by_role('button', name='Stop and transcribe').click()
    expect(page.get_by_role('textbox', name='Your sentence')).to_have_value('A sentence.')
    assert len(calls) == 1


def test_leaving_use_stops_recording_without_sending_it(page, server):
    page.add_init_script(MOCK_RECORDER)
    calls = []
    page.route('**/api/transcribe?*', lambda route: (calls.append(1), route.fulfill(json={'text': 'unexpected'})))
    setup_writing(page, server)
    page.get_by_role('button', name='Speak sentence').click()
    expect(page.get_by_role('button', name='Stop and transcribe')).to_be_visible()
    page.locator('header').get_by_role('link', name='Add').click()
    expect(page.get_by_role('link', name='Back to exercise')).to_be_visible()
    page.wait_for_timeout(100)
    assert not calls and page.evaluate('window.stoppedTracks') == 1
    page.get_by_role('link', name='Back to exercise').click()
    expect(page.get_by_role('button', name='Speak sentence')).to_be_visible()
