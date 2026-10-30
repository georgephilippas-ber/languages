import sqlite3

from src.paths import initialize_data
from src.database import create_table


def test_initialization_preserves_vocabulary_and_history(tmp_path):
    initialize_data(tmp_path)
    entry = tmp_path / "vocabulary/german/german-1.md"
    entry.write_text("## die Sache\n", encoding="utf-8")
    database = tmp_path / "vocabulary/history/history.db"
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO vocabulary_history (term, vocabulary) VALUES ('die Sache', 'GERMAN')")
        connection.execute("CREATE TABLE flashcard_reviews (term TEXT)")
        connection.execute("INSERT INTO flashcard_reviews VALUES ('die Sache')")
    initialize_data(tmp_path)
    with sqlite3.connect(database) as connection:
        create_table(connection)
        assert connection.execute("SELECT term FROM vocabulary_history").fetchall() == [("die Sache",)]
        assert connection.execute("SELECT term FROM flashcard_reviews").fetchall() == [("die Sache",)]
    assert entry.read_text(encoding="utf-8") == "## die Sache\n"
