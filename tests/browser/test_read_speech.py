from playwright.sync_api import expect


def test_read_article_speaks_title_and_summary(page, server):
    page.add_init_script('''
      window.audioCount = 0;
      Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {cancel: () => {}, getVoices: () => []} });
      window.Audio = function(url) { this.pause = () => {}; this.play = () => { window.audioCount++; return Promise.resolve(); }; };
    ''')
    requests = []
    def speech(route):
        requests.append(route.request.post_data_json)
        route.fulfill(status=200, content_type='audio/mpeg', body=b'fake audio')
    page.route('**/api/speech', speech)
    page.route('**/api/read', lambda route: route.fulfill(json={
        'topic': 'physics', 'title': 'Ein neuer Rekord', 'publication': 'Test Publisher',
        'url': 'https://example.com/article', 'publishedAt': '2026-10-29T12:00:00+00:00',
        'retrievedAt': '2026-10-30T07:00:00+00:00', 'summary': 'Forscher melden einen Rekord.', 'words': ['Rekord']}))
    page.goto(server[0] + '/read')
    page.get_by_role('button', name='physics', exact=True).click()
    page.get_by_role('button', name='Retrieve', exact=False).click()
    listen = page.get_by_role('button', name='Listen to article')
    expect(listen).to_be_visible()
    listen.click()
    page.wait_for_function('window.audioCount === 1')
    assert requests == [{'text': 'Ein neuer Rekord. Forscher melden einen Rekord.', 'language': 'DE'}]
    page.reload()
    expect(page.get_by_role('button', name='Listen to article')).to_be_visible()


def test_read_from_selected_word_uses_remainder_and_stops_previous_audio(page, server):
    page.add_init_script('''
      window.played = 0; window.paused = 0;
      Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {cancel: () => {}, getVoices: () => []} });
      window.Audio = function() { this.volume = 1; this.pause = () => {window.paused++}; this.play = () => {window.played++; return Promise.resolve()}; };
    ''')
    requests = []
    def speech(route):
        requests.append(route.request.post_data_json)
        route.fulfill(status=200, content_type='audio/mpeg', body=b'fake')
    page.route('**/api/speech', speech)
    page.route('**/api/read', lambda route: route.fulfill(json={
        'topic': 'physics', 'title': 'Ein neuer Rekord', 'publication': 'Test',
        'url': 'https://example.com', 'publishedAt': '2026-10-29', 'retrievedAt': '2026-10-30',
        'summary': 'Forscher melden einen Rekord.', 'words': ['Rekord']}))
    page.goto(server[0] + '/read')
    page.get_by_role('button', name='Retrieve', exact=False).click()
    page.get_by_role('button', name='Listen to article').click()
    page.wait_for_function('window.played === 1')
    page.get_by_text('melden', exact=True).click(button='right')
    page.get_by_role('menuitem', name='Read aloud from here').click()
    page.wait_for_function('window.played === 2 && window.paused >= 1')
    assert requests[-1]['text'] == 'melden einen Rekord.'
    expect(page.get_by_role('button', name='Stop', exact=True)).to_be_visible()
