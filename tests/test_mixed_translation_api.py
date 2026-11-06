import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from src.domain import DATA_ROOT, CEFRLevel
from src.mixed_translation import build_items, parse_questions, questions_prompt


def row(id_=1, two=False):
    return {'id': id_, 'source_sentence': 'Die Katze sieht den Hund.',
            'segments': ['The ', ' sees the ', '.'] if two else ['The ', ' is here.'],
            'answers': ['cat', 'dog'] if two else ['cat'],
            'hint': 'An animal', 'choices': [['cat', 'dog'], ['cat', 'bird'], ['dog', 'cat'], ['bird', 'dog']] if two else [['cat'], ['dog'], ['bird'], ['horse']], 'correct_choice': 0}


def test_balanced_language_pairs_and_phrasal_default():
    target = Path(DATA_ROOT) / 'vocabulary' / 'english' / 'english-phrasal-verbs-1.md'
    target.write_text('## to set forth\n\n**Definition:** explain.\n', encoding='utf-8')
    for _ in range(5):
        items = build_items(12)
        assert {i['source_language'] for i in items} == {'EN', 'DE', 'FR'}
        assert {(i['source_language'], i['target_language']) for i in items} == {(a, b) for a in ('EN', 'DE', 'FR') for b in ('EN', 'DE', 'FR') if a != b}
        assert all(i['source_language'] != i['target_language'] for i in items)
        assert any(len(i['entries']) == 2 for i in items)
        assert all(e['term'] != 'to set forth' for i in items for e in i['entries'])
    included = build_items(45, True)
    assert any(e['term'] == 'to set forth' for i in included for e in i['entries'])
    assert 'separate blanks' in questions_prompt(items, CEFRLevel.C1, 'produce')


def test_validate_one_and_two_blank_questions():
    items = [{'source_language': 'DE', 'target_language': 'EN', 'entries': [{'term': 'Katze'}]},
             {'source_language': 'DE', 'target_language': 'EN', 'entries': [{'term': 'Katze'}, {'term': 'Hund'}]}]
    questions = parse_questions(json.dumps({'questions': [row(), row(2, True)]}), items, 'recognize')
    assert [len(q['answers']) for q in questions] == [1, 2]
    assert questions[1]['terms'] == ['Katze', 'Hund']
    malformed = row(); malformed['choices'][1] = malformed['choices'][0]
    assert parse_questions(json.dumps({'questions': [malformed]}), items, 'recognize') == []
    malformed = row(); malformed['segments'].append('unexpected')
    assert parse_questions(json.dumps({'questions': [malformed]}), items, 'produce') == []
    unsafe_hint = row(); unsafe_hint['hint'] = 'The answer is cat'
    assert parse_questions(json.dumps({'questions': [unsafe_hint]}), items, 'produce')[0]['hint'] == ''


def test_api_generation_and_contextual_check(fake_openai):
    def generate(kwargs):
        prompt = kwargs['input']
        data = json.loads(prompt.split('Items: ', 1)[1])
        assert len(data) == 1
        return json.dumps({'questions': [row()]})
    fake_openai.reply(generate)
    with TestClient(create_app()) as client:
        response = client.post('/api/mixed-translation', json={'mode': 'recognize', 'count': 1, 'level': 'C1'})
        assert response.status_code == 200
        question = response.json()['questions'][0]
        assert question['sourceLanguage'] != question['targetLanguage']
        answer = client.post('/api/mixed-translation/check', json={'question': question, 'answers': ['CAT']})
        assert answer.status_code == 200 and answer.json()['verdict'] == 'correct'
        fake_openai.reply({'verdict': 'correct', 'corrected_answers': ['feline'], 'comment': 'This fits.'})
        answer = client.post('/api/mixed-translation/check', json={'question': question, 'answers': ['feline']})
        assert answer.status_code == 200 and answer.json()['verdict'] == 'correct'
        answer = client.post('/api/mixed-translation/check', json={'question': question, 'answers': ['', 'extra']})
        assert answer.status_code == 502


@pytest.mark.parametrize('language', ['DE', 'FR'])
def test_lucky_pairs_selected_language_with_english(language):
    items = build_items(12, pair_language=language)
    assert {(item['source_language'], item['target_language']) for item in items} == {('EN', language), (language, 'EN')}
    assert all(item['source_language'] != item['target_language'] for item in items)


@pytest.mark.parametrize('language', ['DE', 'FR'])
def test_api_lucky_language_pair_is_used(fake_openai, language):
    def generate(kwargs):
        items = json.loads(kwargs['input'].split('Items: ', 1)[1])
        assert all({item['source_language'], item['target_language']} == {'EN', language} for item in items)
        return json.dumps({'questions': [row()]})
    fake_openai.reply(generate)
    with TestClient(create_app()) as client:
        response = client.post('/api/mixed-translation', json={'mode': 'produce', 'count': 1, 'level': 'C1', 'pairLanguage': language})
        assert response.status_code == 200
        question = response.json()['questions'][0]
        assert {question['sourceLanguage'], question['targetLanguage']} == {'EN', language}
