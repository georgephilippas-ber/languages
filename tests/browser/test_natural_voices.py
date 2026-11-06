import re
from playwright.sync_api import expect

QUESTION = {'sourceLanguage': 'FR', 'targetLanguage': 'DE', 'sourceSentence': 'Le chat voit le chien.',
            'segments': ['Die ', ' sieht den Hund.'], 'answers': ['Katze'], 'hint': 'An animal',
            'choices': [['Katze'], ['Maus'], ['Vogel'], ['Frau']], 'correctChoice': 0, 'terms': ['le chat']}


def install_speech_stub(page, delayed):
    page.add_init_script('''
      Object.defineProperty(navigator, 'userAgent', { configurable: true, value: 'Mozilla/5.0 Edg/130.0' });
      window.spoken = []; window.listeners = [];
      window.localVoice = {name: 'French local', lang: 'fr-FR', localService: true};
      window.naturalVoice = {name: 'Microsoft Denise Online (Natural)', lang: 'fr-FR', localService: false};
      window.voices = [window.localVoice];
      if (!DELAYED) window.voices.push(window.naturalVoice);
      window.SpeechSynthesisUtterance = function(text) { this.text = text; };
      Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
        getVoices: () => window.voices,
        cancel: () => {},
        addEventListener: (type, cb) => { if (type === 'voiceschanged') window.listeners.push(cb); },
        removeEventListener: (type, cb) => { window.listeners = window.listeners.filter((item) => item !== cb); },
        speak: (utterance) => { window.lastUtterance = utterance; window.spoken.push({text: utterance.text, name: utterance.voice?.name || null, lang: utterance.lang}); }
      }});
      window.loadNatural = () => { window.voices.push(window.naturalVoice); [...window.listeners].forEach((f) => f()); };
      window.failSpeech = () => window.lastUtterance.onerror({error:'network'});
    '''.replace('DELAYED', 'true' if delayed else 'false'))


def prepare(page, server):
    page.route('**/api/mixed-translation', lambda route: route.fulfill(json={'source': 'Mixed', 'questions': [QUESTION]}))
    page.goto(server[0] + '/translate/recognize')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()


def test_natural_voice_is_preferred_and_local_voice_handles_error(page, server):
    install_speech_stub(page, False)
    prepare(page, server)
    page.get_by_role('button', name='Listen to French sentence').click()
    assert page.evaluate('window.spoken') == [{'text': 'Le chat voit le chien.', 'name': 'Microsoft Denise Online (Natural)', 'lang': 'fr-FR'}]
    page.evaluate('window.failSpeech()')
    assert page.evaluate('window.spoken')[-1]['name'] == 'French local'
    expect(page.get_by_role('button', name='Stop')).to_have_attribute('aria-pressed', 'true')


def test_delayed_voice_discovery_and_cancellation(page, server):
    install_speech_stub(page, True)
    prepare(page, server)
    page.get_by_role('button', name='Listen to French sentence').click()
    assert page.evaluate('window.spoken') == []
    page.evaluate('window.loadNatural()')
    assert page.evaluate('window.spoken')[-1]['name'] == 'Microsoft Denise Online (Natural)'
    page.get_by_role('button', name='Stop').click()
    page.evaluate('window.voices = [window.localVoice]')
    page.get_by_role('button', name='Listen to French sentence').click()
    page.get_by_role('button', name='Stop').click()
    page.evaluate('window.loadNatural()')
    page.wait_for_timeout(1000)
    assert len(page.evaluate('window.spoken')) == 1


def test_missing_natural_voice_uses_matching_local_after_wait(page, server):
    install_speech_stub(page, True)
    prepare(page, server)
    page.evaluate("window.voices.push({name:'Microsoft English Online (Natural)', lang:'en-GB', localService:false})")
    page.get_by_role('button', name='Listen to French sentence').click()
    page.wait_for_function('window.spoken.length === 1')
    assert page.evaluate('window.spoken[0].name') == 'French local'
