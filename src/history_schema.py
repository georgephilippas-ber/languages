from sqlite3 import Connection


CREATE_HISTORY = """CREATE TABLE IF NOT EXISTS vocabulary_history (
    id INTEGER PRIMARY KEY,
    term TEXT NOT NULL,
    vocabulary TEXT NOT NULL,
    last_trained_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (vocabulary, term)
)"""


def ensure_history_schema(connection: Connection) -> None:
    """Upgrade the old term-only key transactionally, preserving IDs and timestamps."""
    connection.execute("SAVEPOINT history_schema")
    try:
        connection.execute(CREATE_HISTORY)
        unique_columns = []
        for index in connection.execute("PRAGMA index_list(vocabulary_history)").fetchall():
            if index[2]:
                name = index[1].replace('"', '""')
                unique_columns.append([row[2] for row in connection.execute(f'PRAGMA index_info("{name}")')])
        if ["term"] in unique_columns:
            connection.execute(CREATE_HISTORY.replace("IF NOT EXISTS vocabulary_history", "vocabulary_history_composite"))
            connection.execute("""INSERT INTO vocabulary_history_composite
                (id, term, vocabulary, last_trained_at)
                SELECT id, term, vocabulary, last_trained_at FROM vocabulary_history""")
            connection.execute("DROP TABLE vocabulary_history")
            connection.execute("ALTER TABLE vocabulary_history_composite RENAME TO vocabulary_history")
        connection.execute("RELEASE SAVEPOINT history_schema")
    except Exception:
        connection.execute("ROLLBACK TO SAVEPOINT history_schema")
        connection.execute("RELEASE SAVEPOINT history_schema")
        raise
