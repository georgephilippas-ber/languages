from os.path import sep
from sqlite3 import connect, Connection

from typing import List
from .domain import DATA_ROOT, Vocabulary
from src.history_schema import ensure_history_schema

DATABASE_PATH_ELEMENTS: List[str] = [DATA_ROOT, "vocabulary", "history"]
DATABASE_NAME: str = "history.db"


def get_database_connection() -> Connection:
    return connect(sep.join(DATABASE_PATH_ELEMENTS + [DATABASE_NAME]))


def close_connection(connection: Connection):
    connection.close()


def create_table(connection: Connection):
    ensure_history_schema(connection)


def insert_term(term: str, vocabulary: Vocabulary):
    connection = get_database_connection()

    connection.execute(
        """
        INSERT INTO vocabulary_history (term, vocabulary)
        VALUES (?, ?)
        ON CONFLICT(vocabulary, term) DO UPDATE SET last_trained_at = CURRENT_TIMESTAMP;
        """,
        (term, vocabulary.name),
    )
    connection.commit()
    connection.close()


def get_used_descending(connection: Connection, vocabulary: Vocabulary = Vocabulary.GERMAN) -> List[str]:
    try:
        cursor = connection.execute(
            """
            SELECT term
            FROM vocabulary_history
            WHERE vocabulary = ?
              AND last_trained_at IS NOT NULL
            ORDER BY last_trained_at DESC, id DESC
            """,
            (vocabulary.name,),
        )

        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(e)

        return []
    finally:
        close_connection(connection)


def retrieve_used_terms(vocabulary: Vocabulary):
    connection_ = get_database_connection()
    seen_ = get_used_descending(connection_, vocabulary)
    close_connection(connection_)

    return seen_


if __name__ == "__main__":
    pass
