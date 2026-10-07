import re
from os import listdir
from os.path import dirname, isdir, isfile, sep
from typing import List

from src.domain import Vocabulary

ROOT_PATH_ELEMENTS: List[str] = [dirname(__file__), ".."]

MAX_TERMS_PER_FILE: int = 25


def library_directory(vocabulary_: Vocabulary) -> str:
    return sep.join(ROOT_PATH_ELEMENTS + ["vocabulary", vocabulary_.name.lower()])


def library_file_name(vocabulary_: Vocabulary, file_number_: int) -> str:
    return f"{vocabulary_.name.lower()}-{file_number_}.md"


def library_file_path(vocabulary_: Vocabulary, file_number_: int) -> str:
    return sep.join([library_directory(vocabulary_), library_file_name(vocabulary_, file_number_)])


def library_file_numbers(vocabulary_: Vocabulary) -> List[int]:
    directory_ = library_directory(vocabulary_)
    if not isdir(directory_):
        return []

    return list(range(1, len([file_ for file_ in listdir(directory_) if file_.endswith(".md")]) + 1))


def read_library_file(vocabulary_: Vocabulary, file_number_: int) -> str:
    file_path_ = library_file_path(vocabulary_, file_number_)
    if not isfile(file_path_):
        return ""

    with open(file_path_, "r", encoding="utf-8") as file_:
        return file_.read()


def count_terms(text_: str) -> int:
    return len(re.findall(r"^## ", text_, flags=re.M))


def split_entries(text_: str) -> List[str]:
    return ["## " + chunk_.strip() for chunk_ in re.split(r"^## ", text_, flags=re.M)[1:]]
