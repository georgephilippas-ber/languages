from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from backend.app import create_app
from src.adaptive import allowance, record_answers, select_entries
from src.domain import Vocabulary
from src.database import get_database_connection


def test_correct_answers_including_hints_earn_credit_and_events_are_idempotent():
    vocabulary = Vocabulary.GERMAN
    record_answers('seen', vocabulary, 'produce', [('word', 'seen', False)])
    record_answers('wrong', vocabulary, 'produce', [('word', 'wrong', False)])
    record_answers('hint', vocabulary, 'produce', [('word', 'correct', True)])
    for index in range(5):
        record_answers(f'answer-{index}', vocabulary, 'produce', [('word', 'correct', False)])
    record_answers('answer-4', vocabulary, 'produce', [('word', 'correct', False)])
    assert allowance(vocabulary) == {'available': 6, 'reviews_toward_next': 1}
    assert allowance(Vocabulary.FRENCH)['available'] == 5
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


def test_negative_floor_credit_earning_and_phrasal_exemption():
    entry = '## Example\n\n**Definition:** An example.'
    with TestClient(create_app()) as client:
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == 5
        assert client.post('/api/entries/save', json={'language': 'EN', 'entries': [entry] * 10}).status_code == 200
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == -5
        assert client.post('/api/entries/save', json={'language': 'EN', 'entries': [entry]}).status_code == 400
        assert client.post('/api/entries/save', json={'language': 'EN', 'entries': ['## to set forth\n\n**Definition:** explain.'], 'category': 'phrasal-verbs'}).status_code == 200
        for index in range(5):
            body = {'eventId': str(index), 'language': 'EN', 'skill': 'recognize', 'answers': [{'term': 'to set forth', 'outcome': 'correct'}]}
            assert client.post('/api/exercise-progress', json=body).status_code == 204
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == -5
        for index in range(10):
            body = {'eventId': f'good-{index}', 'language': 'EN', 'skill': 'produce' if index < 5 else 'recognize', 'answers': [{'term': 'word', 'outcome': 'correct', 'assisted': index % 2 == 0}]}
            assert client.post('/api/exercise-progress', json=body).status_code == 204
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == -3
        assert client.post('/api/entries/save', json={'language': 'EN', 'entries': [entry] * 3}).status_code == 400
        assert client.post('/api/entries/save', json={'language': 'EN', 'entries': [entry] * 2}).status_code == 200
        assert client.get('/api/entries/allowance?language=EN').json()['available'] == -5
        assert client.get('/api/entries/allowance?language=FR').json()['available'] == 5


def test_existing_credit_is_reset_once_without_losing_review_remainder():
    with get_database_connection() as db:
        db.execute('CREATE TABLE vocabulary_allowance (vocabulary TEXT PRIMARY KEY, earned_reviews INTEGER NOT NULL DEFAULT 0, words_added INTEGER NOT NULL DEFAULT 0)')
        db.execute("INSERT INTO vocabulary_allowance VALUES ('GERMAN', 12, 7)")
    assert allowance(Vocabulary.GERMAN) == {'available': 5, 'reviews_toward_next': 2}
    record_answers('after-reset', Vocabulary.GERMAN, 'recognize', [('word', 'correct', True)])
    assert allowance(Vocabulary.GERMAN) == {'available': 5, 'reviews_toward_next': 3}


def test_multiword_question_counts_as_one_correct_answer():
    words = [('first', 'correct', True), ('second', 'correct', False)]
    for index in range(5):
        record_answers(f'multi-{index}', Vocabulary.GERMAN, 'writing', words)
    assert allowance(Vocabulary.GERMAN) == {'available': 6, 'reviews_toward_next': 0}
    record_answers('partial', Vocabulary.GERMAN, 'writing', [('first', 'correct', False), ('second', 'wrong', False)])
    assert allowance(Vocabulary.GERMAN) == {'available': 6, 'reviews_toward_next': 0}
