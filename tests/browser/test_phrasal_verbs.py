from pathlib import Path
import pytest
from playwright.sync_api import expect
from src.domain import DATA_ROOT


@pytest.mark.parametrize('mode,endpoint', [(0.0, 'quiz'), (0.9, 'typed')])
def test_phrasal_button_is_english_only_and_starts_scoped_lucky(page, server, mode, endpoint):
    directory = Path(DATA_ROOT) / 'vocabulary' / 'english'
    seed = Path(__file__).resolve().parents[2] / 'seed' / 'en-phrasal-verbs-1.md'
    (directory / 'english-phrasal-verbs-1.md').write_text(seed.read_text())
    requests = []
    question = {'term': 'to get up', 'question': 'I _____ early.', 'choices': ['get up', 'take off', 'set up', 'go on'], 'correctChoice': 0, 'completeSentence': 'I get up early.', 'englishTranslation': 'Rise early.', 'choicesTranslations': [], 'hint': 'Rise.', 'correctAnswer': 'get up'}
    page.route('**/api/' + endpoint, lambda route: (requests.append(route.request.post_data_json), route.fulfill(json={'source':'test', 'questions':[question] * 12})))
    page.goto(server[0] + '/')
    expect(page.locator('header').get_by_role('button', name='Phrasal verbs')).to_have_count(0)
    page.locator('header').get_by_role('button', name='EN', exact=True).click()
    button = page.locator('header').get_by_role('button', name='Phrasal verbs')
    expect(button).to_be_visible()
    page.evaluate('(value) => { Math.random = () => value }', mode)
    button.click()
    expect(page.get_by_role('progressbar')).to_be_visible()
    assert requests[0]['language'] == 'EN' and requests[0]['files'] == 'phrasal-verbs'
    assert requests[0]['level'] == 'C1' and requests[0]['count'] == 12
