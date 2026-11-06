from pathlib import Path
from shutil import rmtree

from src.adding import save_entries
from src.domain import DATA_ROOT, Vocabulary


def test_saving_through_linked_language_directory_updates_repository(tmp_path):
    language_dir = Path(DATA_ROOT) / 'vocabulary' / 'english'
    rmtree(language_dir)
    repository_dir = tmp_path / 'repository' / 'vocabulary' / 'english'
    repository_dir.mkdir(parents=True)
    language_dir.symlink_to(repository_dir, target_is_directory=True)

    result = save_entries(Vocabulary.ENGLISH, ['## linked word\n\n**Definition:** An example.'])

    assert result.saved[0].term == 'linked word'
    assert '## linked word' in (repository_dir / 'english-1.md').read_text()
    assert language_dir.is_symlink()
