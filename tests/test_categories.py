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
