from os.path import sep
from sqlite3 import connect, Connection

from typing import List
from domain import Vocabulary

DATABASE_PATH_ELEMENTS: List[str] = ["..", "vocabulary", "history"]
DATABASE_NAME: str = "history.db"


def get_database_connection() -> Connection:
    return connect(sep.join(DATABASE_PATH_ELEMENTS + [DATABASE_NAME]))


def close_connection(connection: Connection):
    connection.close()


def create_table(connection: Connection):
    connection_.execute("drop table if exists vocabulary_history;")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS vocabulary_history
        (
            id              INTEGER PRIMARY KEY,
            term            TEXT NOT NULL UNIQUE,
            vocabulary      TEXT NOT NULL,
            last_trained_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def insert_term(connection: Connection, term: str, vocabulary: Vocabulary):
    connection.execute(
        """
        INSERT INTO vocabulary_history (term, vocabulary)
        VALUES (?, ?)
        ON CONFLICT(term) DO UPDATE SET vocabulary      = excluded.vocabulary,
                                        last_trained_at = CURRENT_TIMESTAMP;
        """,
        (term, vocabulary.value),
    )
    connection_.commit()


def get_used_descending(connection: Connection, vocabulary: Vocabulary = Vocabulary.GERMAN):
    try:
        cursor = connection.execute(
            """
            SELECT term
            FROM vocabulary_history
            WHERE vocabulary = ?
              AND last_trained_at IS NOT NULL
            ORDER BY last_trained_at DESC, id DESC 
            """,
            (vocabulary.value,),
        )

        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(e)
    finally:
        close_connection(connection)


if __name__ == "__main__":
    connection_ = get_database_connection()
    create_table(connection_)

    insert_term(connection_, "test2", Vocabulary.GERMAN)
    insert_term(connection_, "test44", Vocabulary.GERMAN)
    insert_term(connection_, "tes44t", Vocabulary.GERMAN)
    connection_.commit()

    print(get_used_descending(connection_))
    close_connection(connection_)
