from pathlib import Path
from src.library import split_entries


def test_starter_entries_cover_languages_and_stay_within_file_limit():
    root = Path(__file__).resolve().parent.parent / 'seed'
    expected = {'en': 12, 'de': 13, 'fr': 12}
    for category in ('legal', 'financial'):
        for language, count in expected.items():
            entries = split_entries((root / f'{language}-{category}-1.md').read_text())
            assert len(entries) == count <= 25
            assert len({entry.partition('\n')[0] for entry in entries}) == count
            assert all('**Definition:**' in entry and '**Grammar:**' in entry and '**Example:**' in entry for entry in entries)
            assert all(all(f'**{label}:**' in entry for label in {'en': ('German', 'French'), 'de': ('English', 'French'), 'fr': ('English', 'German')}[language]) for entry in entries)
