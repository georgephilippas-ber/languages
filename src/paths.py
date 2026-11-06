from os import environ
from pathlib import Path
import sqlite3

from src.history_schema import ensure_history_schema
from src.read_sources import initialize_sources


def data_root() -> Path:
    return Path(environ.get("LANGUAGES_DATA") or Path.home() / "tmp" / "languages").expanduser().resolve()


def initialize_data(root: Path) -> None:
    """Create missing storage without replacing vocabulary or resetting history."""
    initialize_sources(root)
    for language in ("english", "french", "german", "history"):
        (root / "vocabulary" / language).mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(root / "vocabulary" / "history" / "history.db") as connection:
        ensure_history_schema(connection)
