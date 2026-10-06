import re
from enum import Enum
from os import listdir
from os.path import dirname, isdir, isfile, sep
from typing import Dict, List

from src.domain import Vocabulary

ROOT_PATH_ELEMENTS: List[str] = [dirname(__file__), ".."]

MAX_TERMS_PER_FILE: int = 25


class Kind(Enum):
    VOCABULARY = ["vocabulary"]
    IDIOMS = ["expressions", "idioms"]
    GRAMMATICAL = ["expressions", "grammatical"]


KIND_NAMES: Dict[str, Kind] = {"vocabulary": Kind.VOCABULARY, "idioms": Kind.IDIOMS, "grammatical": Kind.GRAMMATICAL}


def kind_name(kind_: Kind) -> str:
    return kind_.name.lower()


def kind_directory(kind_: Kind, vocabulary_: Vocabulary) -> str:
    return sep.join(ROOT_PATH_ELEMENTS + kind_.value + [vocabulary_.name.lower()])


def kind_file_name(vocabulary_: Vocabulary, file_number_: int) -> str:
    return f"{vocabulary_.name.lower()}-{file_number_}.md"


def kind_file_path(kind_: Kind, vocabulary_: Vocabulary, file_number_: int) -> str:
    return sep.join([kind_directory(kind_, vocabulary_), kind_file_name(vocabulary_, file_number_)])


def kind_file_numbers(kind_: Kind, vocabulary_: Vocabulary) -> List[int]:
    directory_ = kind_directory(kind_, vocabulary_)
    if not isdir(directory_):
        return []

    return list(range(1, len([file_ for file_ in listdir(directory_) if file_.endswith(".md")]) + 1))


def read_kind_file(kind_: Kind, vocabulary_: Vocabulary, file_number_: int) -> str:
    file_path_ = kind_file_path(kind_, vocabulary_, file_number_)
    if not isfile(file_path_):
        return ""

    with open(file_path_, "r", encoding="utf-8") as file_:
        return file_.read()


def count_terms(text_: str) -> int:
    return len(re.findall(r"^## ", text_, flags=re.M))


def split_entries(text_: str) -> List[str]:
    return ["## " + chunk_.strip() for chunk_ in re.split(r"^## ", text_, flags=re.M)[1:]]
