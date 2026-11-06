from os.path import basename, isfile
from typing import List

from src.configuration import LATEST_FILES_NUMBER
from src.domain import Vocabulary
from src.parser import get_vocabulary_file_numbers, get_vocabulary_file_path
from src.library import CATEGORIES, all_library_files, library_file_numbers

ALL_FILES: str = "all"
LATEST_FILE: str = "latest"
CURRENT_FILE: str = "current"


def latest_file_numbers(vocabulary_: Vocabulary) -> List[int]:
    return get_vocabulary_file_numbers(vocabulary_)[-LATEST_FILES_NUMBER:]


def select_file_numbers(vocabulary_: Vocabulary, selection_: int | str | None) -> List[int]:
    if selection_ is None or selection_ == LATEST_FILE:
        return latest_file_numbers(vocabulary_)
    if selection_ == CURRENT_FILE:
        return latest_file_numbers(vocabulary_)[-1:]
    if selection_ == ALL_FILES:
        return all_library_files(vocabulary_)
    if selection_ in CATEGORIES:
        return library_file_numbers(vocabulary_, selection_)
    if isinstance(selection_, str) and ":" in selection_:
        category_, scope_ = selection_.split(":", 1)
        if category_ in CATEGORIES and scope_ in (CURRENT_FILE, LATEST_FILE):
            numbers_ = library_file_numbers(vocabulary_, category_)
            return numbers_[-1:] if scope_ == CURRENT_FILE else numbers_[-LATEST_FILES_NUMBER:]

    try:
        file_path_ = get_vocabulary_file_path(vocabulary_, selection_)
    except (ValueError, TypeError):
        raise ValueError("Invalid file selection")
    if not isfile(file_path_):
        raise ValueError(f"there is no vocabulary file {file_path_}")

    return [selection_]


def describe_file_numbers(vocabulary_: Vocabulary, file_numbers_: List[int]) -> str:
    names_ = [basename(get_vocabulary_file_path(vocabulary_, i_)) for i_ in file_numbers_]
    if len(names_) > LATEST_FILES_NUMBER and file_numbers_ == get_vocabulary_file_numbers(vocabulary_):
        return "all files (" + ", ".join(names_) + ")"

    return " and ".join(names_) if len(names_) <= 2 else ", ".join(names_[:-1]) + ", and " + names_[-1]
