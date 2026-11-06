from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from src.adding import save_entries
from src.domain import Vocabulary
from src.library import library_directory, library_file_numbers, read_library_file
from src.selection import select_file_numbers


def test_categories_are_independent_and_roll_over():
    vocab = Vocabulary.ENGLISH
    entries = [f"## term {i}\n\n**Definition:** A test term." for i in range(26)]
    save_entries(vocab, entries, "legal")
    save_entries(vocab, ["## yield\n\n**Definition:** A return."], "financial")
    assert library_file_numbers(vocab, "legal") == ["legal:1", "legal:2"]
    assert read_library_file(vocab, "legal:1").count("## ") == 25
    assert select_file_numbers(vocab, "legal") == ["legal:1", "legal:2"]
    assert select_file_numbers(vocab, "all") == [1, "legal:1", "legal:2", "financial:1"]
    assert Path(library_directory(vocab), "english-1.md").exists()
    with TestClient(create_app()) as client:
        response = client.post('/api/flashcards', json={'language': 'EN', 'files': 'legal'})
        assert response.status_code == 200
        assert len(response.json()['cards']) == 26
        response = client.post('/api/entries/save', json={'language': 'EN', 'category': 'financial', 'entries': ['## principal\n\n**Definition:** Original sum.']})
        assert response.status_code == 200
        assert response.json()['fileName'] == 'english-financial-1.md'


def test_phrasal_verbs_are_english_only_and_roll_over():
    import pytest
    from src.library import categories_for
    entries = [f'## to test {i}\n\n**Definition:** A test phrase.' for i in range(51)]
    result = save_entries(Vocabulary.ENGLISH, entries, 'phrasal-verbs')
    assert result.file_name == 'english-phrasal-verbs-3.md'
    assert library_file_numbers(Vocabulary.ENGLISH, 'phrasal-verbs') == [
        'phrasal-verbs:1', 'phrasal-verbs:2', 'phrasal-verbs:3']
    assert [read_library_file(Vocabulary.ENGLISH, f'phrasal-verbs:{i}').count('## ') for i in (1, 2, 3)] == [25, 25, 1]
    assert 'phrasal-verbs' in categories_for(Vocabulary.ENGLISH)
    for language in (Vocabulary.GERMAN, Vocabulary.FRENCH):
        assert 'phrasal-verbs' not in categories_for(language)
        with pytest.raises(ValueError):
            save_entries(language, ['## test\n\n**Definition:** test.'], 'phrasal-verbs')
        with pytest.raises(ValueError):
            select_file_numbers(language, 'phrasal-verbs:1')
    with TestClient(create_app()) as client:
        meta = client.get('/api/meta').json()
        english = next(item for item in meta['languages'] if item['code'] == 'EN')
        assert [item['number'] for item in english['files'] if str(item['number']).startswith('phrasal-verbs:')] == [
            'phrasal-verbs:1', 'phrasal-verbs:2', 'phrasal-verbs:3']
        cards = client.post('/api/flashcards', json={'language': 'EN', 'files': 'phrasal-verbs'})
        assert cards.status_code == 200 and len(cards.json()['cards']) == 51
        assert client.post('/api/flashcards', json={'language': 'DE', 'files': 'phrasal-verbs'}).status_code == 400
        assert client.post('/api/writing', json={'language': 'FR', 'count': 1, 'files': 'phrasal-verbs:1'}).status_code == 400
        assert client.post('/api/entries/save', json={'language': 'DE', 'category': 'phrasal-verbs',
                            'entries': ['## test\n\n**Definition:** test.']}).status_code == 400
