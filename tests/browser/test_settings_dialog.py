import re
from playwright.sync_api import expect


def test_model_theme_and_keys_share_settings_and_persist(page, server):
    page.route('**/api/models', lambda route: route.fulfill(json={'default': 'model-a', 'models': ['model-a', 'model-b']}))
    page.route('**/api/meta', lambda route: route.fulfill(response=route.fetch(headers={'X-OpenAI-Model': ''})))
    requests = []
    def quiz(route):
        requests.append(route.request.headers.get('x-openai-model'))
        route.fulfill(json={'source': 'test', 'questions': [{'term': 'one', 'question': 'This is _____.',
            'choices': ['one', 'two'], 'correctChoice': 0, 'completeSentence': 'This is one.',
            'englishTranslation': 'One thing.', 'choicesTranslations': []}]})
    page.route('**/api/quiz', quiz)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(server[0] + '/')
    header = page.locator('header')
    expect(header.get_by_role('button', name=re.compile('^Model:'))).to_have_count(0)
    expect(header.get_by_role('button', name=re.compile('^Theme:'))).to_have_count(0)
    header.get_by_role('button', name=re.compile('^Languages menu')).click()
    page.get_by_role('menuitem', name='Settings', exact=True).click()
    dialog = page.get_by_role('dialog', name='Settings')
    expect(dialog).to_be_visible()
    model = dialog.get_by_label('OpenAI model')
    expect(model).to_be_enabled()
    expect(model).to_have_value('model-a')
    model.select_option('model-b')
    dialog.get_by_label('Colour theme').select_option('dark')
    expect(page.locator('html')).to_have_class(re.compile('dark'))
    expect(dialog.get_by_label('New OpenAI API key')).to_be_visible()
    expect(dialog.get_by_label('New ElevenLabs API key')).to_be_visible()
    dialog.get_by_role('button', name='Close').click()
    page.reload()
    expect(page.locator('html')).to_have_class(re.compile('dark'))
    header.get_by_role('button', name=re.compile('^Languages menu')).click()
    page.get_by_role('menuitem', name='Settings', exact=True).click()
    expect(dialog.get_by_label('OpenAI model')).to_have_value('model-b')
    expect(dialog.get_by_label('Colour theme')).to_have_value('dark')
    dialog.get_by_label('Colour theme').select_option('light')
    expect(page.locator('html')).not_to_have_class(re.compile('dark'))
    dialog.get_by_role('button', name='Close').click()
    page.goto(server[0] + '/quiz')
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    expect(page.get_by_role('button', name='A one')).to_be_visible()
    assert requests == ['model-b']
