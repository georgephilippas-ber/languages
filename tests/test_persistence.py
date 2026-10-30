from pathlib import Path
import os
import sqlite3
import subprocess
import sys

import pytest

from src import adding
from src.database import insert_term, retrieve_used_terms
from src.domain import DATA_ROOT, Vocabulary
from src.history_schema import ensure_history_schema
from src.library import library_directory, library_file_numbers, library_file_path, read_library_file, count_terms
from src.parser import get_vocabulary_file_numbers, parse_vocabulary_to_list
from src.selection import select_file_numbers
from src.flashcards import select_library_file_numbers
from src.openai_integration import sample_alternatives_


def test_legacy_history_upgrade_preserves_rows_and_flashcards(tmp_path):
    with sqlite3.connect(tmp_path / "history.db") as connection:
        connection.execute("CREATE TABLE vocabulary_history (id INTEGER PRIMARY KEY, term TEXT NOT NULL UNIQUE, vocabulary TEXT NOT NULL, last_trained_at DATETIME)")
        connection.execute("INSERT INTO vocabulary_history VALUES (42, 'chat', 'FRENCH', '2026-01-02 03:04:05')")
        connection.execute("CREATE TABLE flashcard_reviews (term TEXT)")
        connection.execute("INSERT INTO flashcard_reviews VALUES ('chat')")
        for _ in range(2):
            ensure_history_schema(connection)
        assert connection.execute("SELECT * FROM vocabulary_history").fetchall() == [(42, 'chat', 'FRENCH', '2026-01-02 03:04:05')]
        connection.execute("INSERT INTO vocabulary_history (term, vocabulary) VALUES ('chat', 'ENGLISH')")
        assert connection.execute("SELECT term FROM flashcard_reviews").fetchall() == [('chat',)]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO vocabulary_history (term, vocabulary) VALUES ('chat', 'ENGLISH')")


def test_same_spelling_keeps_independent_language_history():
    insert_term("chat", Vocabulary.FRENCH)
    insert_term("chat", Vocabulary.ENGLISH)
    insert_term("chat", Vocabulary.FRENCH)
    assert retrieve_used_terms(Vocabulary.FRENCH) == ["chat"]
    assert retrieve_used_terms(Vocabulary.ENGLISH) == ["chat"]


def test_failed_atomic_replace_keeps_original_file(monkeypatch):
    before = read_library_file(Vocabulary.GERMAN, 1)
    def fail(*args):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(adding.os, "replace", fail)
    with pytest.raises(OSError, match="disk failure"):
        adding.save_entries(Vocabulary.GERMAN, ["## die Krähe\n\n**Definition:** A bird."])
    assert read_library_file(Vocabulary.GERMAN, 1) == before
    assert not list(Path(library_directory(Vocabulary.GERMAN)).glob('.entry-*.tmp'))


def test_parallel_process_saves_keep_all_entries_and_rollover():
    script = '''import sys,time
from src import adding
from src.domain import Vocabulary
original=adding.read_library_file
def slow(*args):
    text=original(*args)
    time.sleep(.015)
    return text
adding.read_library_file=slow
adding.save_entries(Vocabulary.GERMAN,[f"## concurrent {sys.argv[1]}-{i}\\n\\n**Definition:** An object." for i in range(10)])
'''
    env = dict(os.environ, LANGUAGES_DATA=DATA_ROOT)
    processes = [subprocess.Popen([sys.executable, '-c', script, str(i)], env=env, cwd=Path(__file__).resolve().parent.parent) for i in range(4)]
    try:
        assert all(process.wait(timeout=30) == 0 for process in processes)
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill(); process.wait()
    entries = parse_vocabulary_to_list(Vocabulary.GERMAN)
    assert len(entries) == 52
    assert {entry.term for entry in entries if entry.term.startswith('concurrent')} == {
        f'concurrent {worker}-{i}' for worker in range(4) for i in range(10)}
    assert all(count_terms(read_library_file(Vocabulary.GERMAN, n)) <= 25 for n in library_file_numbers(Vocabulary.GERMAN))


def test_file_discovery_and_quiz_alternatives_handle_gaps():
    directory = Path(library_directory(Vocabulary.GERMAN))
    (directory / 'german-3.md').write_text('## third\n\n**Definition:** Third term.\n')
    (directory / 'german-10.md').write_text('## tenth\n\n**Definition:** Tenth term.\n')
    for name in ['notes.md', 'french-2.md', 'german-0.md', 'german-02.md', 'german-4.md.bak']:
        (directory / name).write_text('not vocabulary')
    (directory / 'german-5.md').mkdir()
    assert library_file_numbers(Vocabulary.GERMAN) == [1, 3, 10]
    assert get_vocabulary_file_numbers(Vocabulary.GERMAN) == [1, 3, 10]
    assert select_file_numbers(Vocabulary.GERMAN, 'latest') == [3, 10]
    assert select_library_file_numbers(Vocabulary.GERMAN, 'current') == [10]
    assert {'third', 'tenth'} <= {entry.term for entry in parse_vocabulary_to_list(Vocabulary.GERMAN)}
    assert 'third' in sample_alternatives_('tenth', ['tenth'], Vocabulary.GERMAN, [10], 3, {})
    assert adding.target_file_number(Vocabulary.GERMAN) == 10
