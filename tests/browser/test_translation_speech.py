import re
import pytest
from playwright.sync_api import expect

QUESTION = {'sourceLanguage': 'FR', 'targetLanguage': 'DE', 'sourceSentence': 'Le chat voit le chien.',
            'segments': ['Die ', ' sieht den Hund.'], 'answers': ['Katze'], 'hint': 'An animal',
            'choices': [['Katze'], ['Maus'], ['Vogel'], ['Frau']], 'correctChoice': 0, 'terms': ['le chat']}


@pytest.mark.parametrize('mode', ['recognize', 'produce'])
def test_translation_listens_to_both_languages_without_revealing_answer(page, server, mode):
    url, _ = server
    page.add_init_script('''
      window.spoken = [];
      window.SpeechSynthesisUtterance = function(text) { this.text = text; };
      Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
        getVoices: () => [], cancel: () => {},
        speak: (utterance) => window.spoken.push({text: utterance.text, lang: utterance.lang})
      }});
    ''')
    page.route('**/api/mixed-translation', lambda route: route.fulfill(json={'source': 'Mixed', 'questions': [QUESTION]}))
    page.route('**/api/mixed-translation/check', lambda route: route.fulfill(json={'verdict': 'correct', 'correctedAnswers': ['Katze'], 'comment': ''}))
    page.goto(url + '/translate/' + mode)
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    original = page.get_by_role('button', name='Listen to French sentence')
    translation = page.get_by_role('button', name='Listen to German translation')
    expect(original).to_be_visible()
    expect(translation).to_have_count(0)
    original.click()
    assert page.evaluate('window.spoken')[-1] == {'text': 'Le chat voit le chien.', 'lang': 'fr-FR'}
    if mode == 'recognize':
        page.get_by_role('button', name=re.compile('Katze')).click()
    else:
        page.get_by_role('textbox', name='Translation blank 1').fill('Katze')
        page.get_by_role('button', name=re.compile('^Check')).click()
    expect(translation).to_be_visible()
    translation.click()
    assert page.evaluate('window.spoken')[-1] == {'text': 'Die Katze sieht den Hund.', 'lang': 'de-DE'}
    expect(page.get_by_role('button', name='Listen to French sentence')).to_have_attribute('aria-pressed', 'false')
    expect(page.get_by_role('button', name='Stop')).to_have_attribute('aria-pressed', 'true')
