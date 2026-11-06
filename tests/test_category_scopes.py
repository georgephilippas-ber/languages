from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from src.domain import DATA_ROOT, Vocabulary
from src.selection import select_file_numbers


def prepare_files():
    directory = Path(DATA_ROOT) / 'vocabulary' / 'english'
    for category in ('general', 'legal', 'financial', 'phrasal-verbs'):
        numbers = (3, 7) if category == 'general' else (1, 3, 7)
        for number in numbers:
            prefix = '' if category == 'general' else f'{category}-'
            path = directory / f'english-{prefix}{number}.md'
            path.write_text(''.join(f'## {category} {number}-{index}\n\n**Definition:** Test.\n\n'
                                    for index in range(2)), encoding='utf-8')


def test_each_category_last_one_last_two_and_entire():
    prepare_files()
    for category in ('general', 'legal', 'financial', 'phrasal-verbs'):
        ids = [1, 3, 7] if category == 'general' else [f'{category}:{n}' for n in (1, 3, 7)]
        assert select_file_numbers(Vocabulary.ENGLISH, f'{category}:current') == ids[-1:]
        assert select_file_numbers(Vocabulary.ENGLISH, f'{category}:latest') == ids[-2:]
        assert select_file_numbers(Vocabulary.ENGLISH, category) == ids
    assert select_file_numbers(Vocabulary.ENGLISH, 'latest') == [3, 7]
    assert select_file_numbers(Vocabulary.ENGLISH, 'current') == [7]
    assert select_file_numbers(Vocabulary.ENGLISH, 'legal:1') == ['legal:1']
    assert len(select_file_numbers(Vocabulary.ENGLISH, 'all')) == 12
    with pytest.raises(ValueError):
        select_file_numbers(Vocabulary.FRENCH, 'phrasal-verbs:latest')


def test_category_scopes_are_accepted_by_api_and_limit_the_source():
    prepare_files()
    with TestClient(create_app()) as client:
        for category in ('general', 'legal', 'financial', 'phrasal-verbs'):
            for scope, expected in (('current', [7]), ('latest', [3, 7]), ('entire', [1, 3, 7])):
                selection = category if scope == 'entire' else f'{category}:{scope}'
                response = client.post('/api/writing', json={'language': 'EN', 'count': 1, 'files': selection})
                assert response.status_code == 200, response.text
                prefix = '' if category == 'general' else f'{category}-'
                source = response.json()['source']
                for number in expected:
                    assert f'english-{prefix}{number}.md' in source
                if scope != 'entire':
                    assert f'english-{prefix}1.md' not in source
        response = client.post('/api/writing', json={'language': 'EN', 'count': 1, 'files': 'all'})
        assert response.status_code == 200
        source = response.json()['source']
        assert all(name in source for name in ('english-1.md', 'english-legal-1.md',
                                                'english-financial-1.md', 'english-phrasal-verbs-1.md'))
        assert client.post('/api/writing', json={'language': 'DE', 'count': 1,
                                                  'files': 'phrasal-verbs:latest'}).status_code == 400


@pytest.mark.parametrize('language', [Vocabulary.GERMAN, Vocabulary.FRENCH])
def test_category_scopes_in_other_languages(language):
    directory = Path(DATA_ROOT) / 'vocabulary' / language.name.lower()
    for category in ('general', 'legal', 'financial'):
        for number in (2, 4):
            prefix = '' if category == 'general' else f'{category}-'
            (directory / f'{language.name.lower()}-{prefix}{number}.md').write_text(
                f'## {category} {number}\n\n**Definition:** test.\n', encoding='utf-8')
        expected = [2, 4] if category == 'general' else [f'{category}:2', f'{category}:4']
        assert select_file_numbers(language, f'{category}:current') == expected[-1:]
        assert select_file_numbers(language, f'{category}:latest') == expected
        assert select_file_numbers(language, category)[-2:] == expected
    with pytest.raises(ValueError):
        select_file_numbers(language, 'phrasal-verbs:current')
