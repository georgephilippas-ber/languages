import re
from playwright.sync_api import expect


def test_audio_uses_elevenlabs_throughout_the_app(page, server):
    page.add_init_script('''
      window.spoken = []; window.audioCount = 0;
      window.SpeechSynthesisUtterance = function(text) { this.text = text; };
      Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
        getVoices: () => [], cancel: () => {}, speak: (u) => window.spoken.push(u.text)
      }});
      window.Audio = function(url) { this.url = url; this.pause = () => {}; this.play = () => { window.audioCount++; return Promise.resolve(); }; };
    ''')
    requests = []
    def speech(route):
        requests.append(route.request.post_data_json)
        route.fulfill(status=200, content_type='audio/mpeg', body=b'fake audio')
    page.route('**/api/speech', speech)
    question = {'sourceLanguage': 'FR', 'targetLanguage': 'DE', 'sourceSentence': 'Le chat dort.',
                'segments': ['Die ', ' schläft.'], 'answers': ['Katze'], 'hint': 'An animal',
                'choices': [['Katze'], ['Maus'], ['Vogel'], ['Frau']], 'correctChoice': 0, 'terms': ['le chat']}
    page.route('**/api/mixed-translation', lambda route: route.fulfill(json={'source': 'Mixed', 'questions': [question]}))
    page.goto(server[0] + '/translate/recognize')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('button', name='Listen to French sentence').click()
    page.wait_for_function('window.audioCount === 1')
    assert requests[0] == {'text': 'Le chat dort.', 'language': 'FR'}
    assert page.evaluate('window.spoken') == []
    page.get_by_role('button', name=re.compile('Katze')).click()
    page.get_by_role('button', name='Listen to German translation').click()
    page.wait_for_function('window.audioCount === 2')
    assert requests[1] == {'text': 'Die Katze schläft.', 'language': 'DE'}
    expect(page.get_by_role('button', name='Listen to French sentence')).to_have_attribute('aria-pressed', 'false')


def test_unavailable_service_uses_browser_voice_and_explains_why(page, server):
    page.add_init_script('''
      window.spoken = [];
      window.SpeechSynthesisUtterance = function(text) { this.text = text; };
      Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
        getVoices: () => [{name:'Local French', lang:'fr-FR', localService:true}],
        cancel: () => {}, speak: (utterance) => window.spoken.push(utterance.text)
      }});
    ''')
    page.route('**/api/speech', lambda route: route.fulfill(status=503, json={'detail': 'unavailable'}))
    question = {'sourceLanguage': 'FR', 'targetLanguage': 'DE', 'sourceSentence': 'Le chat dort.',
                'segments': ['Die ', ' schläft.'], 'answers': ['Katze'], 'hint': 'An animal',
                'choices': [['Katze'], ['Maus'], ['Vogel'], ['Frau']], 'correctChoice': 0, 'terms': ['le chat']}
    page.route('**/api/mixed-translation', lambda route: route.fulfill(json={'source': 'Mixed', 'questions': [question]}))
    page.goto(server[0] + '/translate/recognize')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('button', name='Listen to French sentence').click()
    expect(page.get_by_role('status').filter(has_text='ElevenLabs unavailable; using browser voice.')).to_be_visible()
    page.wait_for_function('window.spoken.length === 1')
    assert page.evaluate('window.spoken[0]') == 'Le chat dort.'


def test_missing_key_explains_browser_voice_fallback(page, server):
    page.add_init_script('''
      window.spoken = [];
      window.SpeechSynthesisUtterance = function(text) { this.text = text; };
      Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
        getVoices: () => [{name:'Local French', lang:'fr-FR', localService:true}],
        cancel: () => {}, speak: (utterance) => window.spoken.push(utterance.text)
      }});
    ''')
    page.route('**/api/speech', lambda route: route.fulfill(status=404, json={'detail': 'not configured'}))
    question = {'sourceLanguage': 'FR', 'targetLanguage': 'DE', 'sourceSentence': 'Le chat dort.',
                'segments': ['Die ', ' schläft.'], 'answers': ['Katze'], 'hint': 'An animal',
                'choices': [['Katze'], ['Maus'], ['Vogel'], ['Frau']], 'correctChoice': 0, 'terms': ['le chat']}
    page.route('**/api/mixed-translation', lambda route: route.fulfill(json={'source': 'Mixed', 'questions': [question]}))
    page.goto(server[0] + '/translate/recognize')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.get_by_role('button', name='Listen to French sentence').click()
    expect(page.get_by_role('status').filter(has_text='ElevenLabs key not set; using browser voice.')).to_be_visible()
    page.wait_for_function('window.spoken.length === 1')
