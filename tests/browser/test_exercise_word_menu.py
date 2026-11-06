import re
from playwright.sync_api import expect


def right_click_word(page, locator, word):
    point = locator.evaluate('''(element, word) => {
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      let node; while (node = walker.nextNode()) {
        const index = node.textContent.indexOf(word);
        if (index < 0) continue;
        const range = document.createRange(); range.setStart(node, index); range.setEnd(node, index + word.length);
        const r = range.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2};
      }
    }''', word)
    assert point is not None
    page.mouse.click(point['x'], point['y'], button='right')


def test_exercise_word_speech_and_queue_without_navigation(page, server):
    page.add_init_script('''
      Object.defineProperty(window, 'speechSynthesis', {configurable:true,value:{cancel:()=>{},getVoices:()=>[]}});
      window.Audio = function() { this.volume=1; this.pause=()=>{}; this.play=()=>Promise.resolve() };
    ''')
    question = {'term': 'Rekord', 'question': 'Ein neuer Rekord ist _____.', 'choices': ['beeindruckend', 'klein'], 'correctChoice': 0,
                'completeSentence': 'Ein neuer Rekord ist beeindruckend.', 'englishTranslation': 'A new record is impressive.', 'choicesTranslations': ['impressive', 'small']}
    page.route('**/api/quiz', lambda route: route.fulfill(json={'source': 'test', 'questions': [question]}))
    speech = []
    page.route('**/api/speech', lambda route: (speech.append(route.request.post_data_json), route.fulfill(status=200, content_type='audio/mpeg', body=b'fake')))
    page.goto(server[0] + '/quiz')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    sentence = page.get_by_text('Ein neuer Rekord ist', exact=False).first
    right_click_word(page, sentence, 'Rekord')
    menu = page.get_by_role('menu', name='Options for Rekord')
    expect(menu).to_be_visible()
    expect(menu.get_by_label('Word language')).to_have_value('DE')
    menu.get_by_role('menuitem', name='Speak word').click()
    page.wait_for_timeout(150)
    assert speech == [{'text': 'Rekord', 'language': 'DE'}]
    right_click_word(page, sentence, 'Rekord')
    page.get_by_role('menuitem', name='Financial').click()
    assert page.url.endswith('/quiz')
    drafts = page.evaluate("JSON.parse(localStorage.getItem('languages.drafts'))")
    assert len(drafts) == 1 and drafts[0]['request'] == 'Rekord' and drafts[0]['category'] == 'financial' and drafts[0]['status'] == 'queued'
    right_click_word(page, sentence, 'Rekord')
    page.get_by_role('menuitem', name='General').click()
    assert len(page.evaluate("JSON.parse(localStorage.getItem('languages.drafts'))")) == 1
    page.keyboard.press('1')
    translation = page.get_by_role('region', name='Feedback').get_by_text('A new record is impressive.')
    expect(translation).to_be_visible()
    right_click_word(page, translation, 'record')
    expect(page.get_by_label('Word language')).to_have_value('EN')
    page.get_by_role('menuitem', name='Legal').click()
    assert page.evaluate("JSON.parse(localStorage.getItem('languages.drafts'))")[1]['language'] == 'EN'


def test_mixed_languages_and_choices_use_their_own_language(page, server):
    question = {'sourceLanguage': 'DE', 'targetLanguage': 'FR', 'sourceSentence': 'Die Katze sieht den Hund.',
                'segments': ['Le ', ' voit le ', '.'], 'answers': ['chat', 'chien'], 'hint': 'Two animals',
                'choices': [['chat', 'chien'], ['chat', 'oiseau'], ['chien', 'chat'], ['oiseau', 'chien']],
                'correctChoice': 0, 'terms': ['die Katze', 'der Hund']}
    page.route('**/api/mixed-translation', lambda route: route.fulfill(json={'source': 'Mixed', 'questions': [question]}))
    page.goto(server[0] + '/translate/recognize')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    sentence = page.get_by_text('Die Katze sieht den Hund.')
    right_click_word(page, sentence, 'Katze')
    expect(page.get_by_label('Word language')).to_have_value('DE')
    page.keyboard.press('Escape')
    choice = page.get_by_role('button', name='chat · chien', exact=False).first
    right_click_word(page, choice, 'chat')
    expect(page.get_by_label('Word language')).to_have_value('FR')
    page.get_by_label('Word language').select_option('EN')
    page.get_by_role('menuitem', name='Phrasal Verbs').click()
    draft = page.evaluate("JSON.parse(localStorage.getItem('languages.drafts'))[0]")
    assert draft['language'] == 'EN' and draft['category'] == 'phrasal-verbs'
