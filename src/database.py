from os.path import sep
from sqlite3 import connect, Connection

from typing import List

DATABASE_PATH_ELEMENTS: List[str] = ["..", "vocabulary", "history"]
DATABASE_NAME: str = "history.db"


def get_database_connection() -> Connection:
    return connect(sep.join(DATABASE_PATH_ELEMENTS + [DATABASE_NAME]))


def close_connection(connection: Connection):
    connection.close()


def create_table(connection: Connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS vocabulary
        (
            id              INTEGER PRIMARY KEY,
            term            TEXT NOT NULL,
            language        TEXT NOT NULL,
            last_trained_at TEXT
        )
        """
    )


if __name__ == "__main__":
    connection_ = get_database_connection()
    close_connection(connection_)
