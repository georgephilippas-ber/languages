from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from backend.app import create_app
from src.adaptive import allowance, record_answers, select_entries
from src.domain import Vocabulary
from src.database import get_database_connection


def test_only_real_unaided_answers_earn_credit_and_events_are_idempotent():
    vocabulary = Vocabulary.GERMAN
    record_answers('seen', vocabulary, 'produce', [('word', 'seen', False)])
    record_answers('wrong', vocabulary, 'produce', [('word', 'wrong', False)])
    record_answers('hint', vocabulary, 'produce', [('word', 'correct', True)])
    for index in range(5):
        record_answers(f'answer-{index}', vocabulary, 'produce', [('word', 'correct', False)])
    record_answers('answer-4', vocabulary, 'produce', [('word', 'correct', False)])
    assert allowance(vocabulary) == {'available': 11, 'reviews_toward_next': 0}
    assert allowance(Vocabulary.FRENCH)['available'] == 10
    with get_database_connection() as db:
        assert db.execute('select attempts, mistakes from exercise_progress where term=?', ('word',)).fetchone() == (7, 1)
        assert db.execute('select count(*) from exercise_views').fetchone()[0] == 1


def test_adaptive_prefers_due_and_new_and_does_not_repeat_until_needed(monkeypatch):
    from src import adaptive
    record_answers('mistake', Vocabulary.FRENCH, 'produce', [('difficult', 'wrong', False)])
    record_answers('easy', Vocabulary.FRENCH, 'produce', [('easy', 'correct', False)])
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    with get_database_connection() as db:
        db.execute('update exercise_progress set due_at=?, last_answered=? where term=?', (old, old, 'difficult'))
    monkeypatch.setattr(adaptive, 'choices', lambda candidates, weights, k: [max(candidates, key=lambda i: weights[i])])
    entries = [SimpleNamespace(term=term) for term in ['easy', 'new', 'difficult']]
    assert [item.term for item in select_entries(entries, Vocabulary.FRENCH, 'produce', 4)] == ['difficult', 'new', 'easy', 'difficult']
    # Another skill has its own history.
    assert [item.term for item in select_entries(entries, Vocabulary.FRENCH, 'recognize', 3)] == ['easy', 'new', 'difficult']


def test_allowance_enforced_by_api_and_phrasal_verbs_exempt():
    entry = '## Example\n\n**Definition:** An example.'
    with TestClient(create_app()) as client:
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == 10
        response = client.post('/api/entries/save', json={'language': 'EN', 'entries': [entry] * 11})
        assert response.status_code == 400
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == 10
        assert client.post('/api/entries/save', json={'language': 'EN', 'entries': [entry] * 10}).status_code == 200
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == 0
        assert client.post('/api/entries/save', json={'language': 'EN', 'entries': ['## to set forth\n\n**Definition:** explain.'], 'category': 'phrasal-verbs'}).status_code == 200
        for index in range(5):
            body = {'eventId': str(index), 'language': 'EN', 'skill': 'recognize', 'answers': [{'term': 'to set forth', 'outcome': 'correct'}]}
            assert client.post('/api/exercise-progress', json=body).status_code == 204
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == 0
        for index in range(5):
            body = {'eventId': f'good-{index}', 'language': 'EN', 'skill': 'produce', 'answers': [{'term': 'word', 'outcome': 'correct'}]}
            assert client.post('/api/exercise-progress', json=body).status_code == 204
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == 1
        assert client.get('/api/entries/allowance?language=FR').json()['available'] == 10
