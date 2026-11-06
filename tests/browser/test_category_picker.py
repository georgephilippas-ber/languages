import re
from pathlib import Path

import pytest
from playwright.sync_api import expect
from src.domain import DATA_ROOT


def prepare_files():
    directory = Path(DATA_ROOT) / 'vocabulary' / 'english'
    seed = Path(__file__).resolve().parents[2] / 'seed'
    for number in (1, 2):
        (directory / f'english-phrasal-verbs-{number}.md').write_text(
            (seed / f'en-phrasal-verbs-{number}.md').read_text(encoding='utf-8'), encoding='utf-8')
    for category in ('general', 'legal', 'financial', 'phrasal-verbs'):
        numbers = (3, 7) if category == 'general' else ((7,) if category == 'phrasal-verbs' else (1, 3, 7))
        for number in numbers:
            prefix = '' if category == 'general' else f'{category}-'
            (directory / f'english-{prefix}{number}.md').write_text(
                ''.join(f'## {category} {number}-{index}\n\n**Definition:** test.\n\n' for index in range(2)),
                encoding='utf-8')


@pytest.mark.parametrize('path,endpoint', [('/quiz', 'quiz'), ('/typed', 'typed'), ('/writing', 'writing')])
def test_each_exercise_offers_category_scopes_and_all(page, server, path, endpoint):
    prepare_files()
    url, _ = server
    page.goto(url + '/')
    page.get_by_role('button', name='EN', exact=True).click()
    page.goto(url + path)
    categories = page.get_by_role('group', name='Vocabulary category')
    for label in ('General', 'Legal', 'Financial', 'Phrasal Verbs'):
        categories.get_by_role('button', name=re.compile('^' + label)).click()
        assert categories.get_by_role('button', name=re.compile('^' + label)).get_attribute('aria-pressed') == 'true'
        files = page.get_by_role('group', name=f'Files in {label}')
        assert files.get_by_role('button', name=re.compile('^Last file')).is_visible()
        assert files.get_by_role('button', name=re.compile('^Last two files')).is_visible()
        assert files.get_by_role('button', name=re.compile('^Entire category')).is_visible()
        files.get_by_role('button', name=re.compile('^Last file')).click()
        expect(files.get_by_role('button', name=re.compile('^Last file'))).to_have_attribute('aria-pressed', 'true')
        files.get_by_role('button', name=re.compile('^Last two files')).click()
        expect(files.get_by_role('button', name=re.compile('^Last two files'))).to_have_attribute('aria-pressed', 'true')
        files.get_by_role('button', name=re.compile('^Entire category')).click()
        expect(files.get_by_role('button', name=re.compile('^Entire category'))).to_have_attribute('aria-pressed', 'true')
    phrasal = page.get_by_role('group', name='Files in Phrasal Verbs')
    expect(phrasal.get_by_role('button', name=re.compile('^Last file'))).to_contain_text('2 terms')
    expect(phrasal.get_by_role('button', name=re.compile('^Last two files'))).to_contain_text('27 terms')
    expect(phrasal.get_by_role('button', name=re.compile('^Entire category'))).to_contain_text('52 terms')
    phrasal.get_by_role('button', name=re.compile('^Last two files')).click()
    requests = []
    def generate(route):
        requests.append(route.request.post_data_json)
        if endpoint == 'quiz':
            payload = {'questions': [{'term': 'term', 'question': 'Here is _____.', 'choices': ['one', 'two'],
                                      'correctChoice': 0, 'completeSentence': 'Here is one.',
                                      'englishTranslation': 'Here is one.', 'choicesTranslations': ['one', 'two']}]}
        elif endpoint == 'typed':
            payload = {'questions': [{'term': 'term', 'question': 'Here is _____.', 'hint': 'hint',
                                      'correctAnswer': 'one', 'completeSentence': 'Here is one.',
                                      'englishTranslation': 'Here is one.'}]}
        else:
            payload = {'rounds': [[{'term': 'first', 'fileName': 'test', 'hint': 'one'},
                                    {'term': 'second', 'fileName': 'test', 'hint': 'two'}]]}
        route.fulfill(json={'source': 'test', **payload})
    page.route('**/api/' + endpoint, generate)
    page.get_by_role('button', name=re.compile(r'^Start \d+')).click()
    page.wait_for_function('() => document.querySelector("[aria-label=\\"End exercise\\"]") !== null')
    assert requests[-1]['files'] == 'phrasal-verbs:latest'


def test_all_categories_and_saved_single_file_are_clear(page, server):
    prepare_files()
    url, _ = server
    page.goto(url + '/')
    page.get_by_role('button', name='EN', exact=True).click()
    page.evaluate("localStorage.setItem('languages.settings.typed', JSON.stringify({level:'C1', count:8, files:'legal:3'}))")
    page.goto(url + '/typed')
    expect(page.get_by_text('Previously selected: english-legal-3.md')).to_be_visible()
    categories = page.get_by_role('group', name='Vocabulary category')
    categories.get_by_role('button', name=re.compile(r'^All categories')).click()
    expect(categories.get_by_role('button', name=re.compile(r'^All categories'))).to_have_attribute('aria-pressed', 'true')
    expect(page.get_by_role('group', name=re.compile(r'^Files in'))).to_have_count(0)
    page.reload()
    expect(categories.get_by_role('button', name=re.compile(r'^All categories'))).to_have_attribute('aria-pressed', 'true')
