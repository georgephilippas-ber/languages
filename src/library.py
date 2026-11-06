import re
from os import listdir
from os.path import isdir, isfile, sep
from typing import List

from src.domain import DATA_ROOT, Vocabulary

ROOT_PATH_ELEMENTS: List[str] = [DATA_ROOT]

MAX_TERMS_PER_FILE: int = 25


def library_directory(vocabulary_: Vocabulary) -> str:
    return sep.join(ROOT_PATH_ELEMENTS + ["vocabulary", vocabulary_.name.lower()])


CATEGORIES = ("general", "legal", "financial", "phrasal-verbs")


def categories_for(vocabulary_: Vocabulary) -> tuple[str, ...]:
    return CATEGORIES if vocabulary_ == Vocabulary.ENGLISH else CATEGORIES[:-1]


def library_file_name(vocabulary_: Vocabulary, file_number_: int | str) -> str:
    category_, number_ = file_parts(file_number_)
    if category_ not in categories_for(vocabulary_):
        raise ValueError("This category is available only for English")
    prefix_ = "" if category_ == "general" else category_ + "-"
    return f"{vocabulary_.name.lower()}-{prefix_}{number_}.md"


def file_parts(file_number_: int | str) -> tuple[str, int]:
    if isinstance(file_number_, int):
        return "general", file_number_
    category_, number_ = file_number_.split(":", 1)
    if category_ not in CATEGORIES[1:] or not number_.isdigit() or int(number_) < 1:
        raise ValueError("Invalid file identifier")
    return category_, int(number_)


def file_id(category_: str, number_: int) -> int | str:
    if category_ not in CATEGORIES or number_ < 1:
        raise ValueError("Invalid category or file number")
    return number_ if category_ == "general" else f"{category_}:{number_}"


def library_file_path(vocabulary_: Vocabulary, file_number_: int | str) -> str:
    return sep.join([library_directory(vocabulary_), library_file_name(vocabulary_, file_number_)])


def library_file_numbers(vocabulary_: Vocabulary, category_: str = "general") -> List[int | str]:
    if category_ not in categories_for(vocabulary_):
        raise ValueError("Invalid category for this language")
    directory_ = library_directory(vocabulary_)
    if not isdir(directory_):
        return []
    prefix_ = "" if category_ == "general" else category_ + "-"
    pattern_ = re.compile(rf"{vocabulary_.name.lower()}-{prefix_}([1-9][0-9]*)\.md")
    numbers_ = sorted(int(match_.group(1)) for file_ in listdir(directory_)
                      if (match_ := pattern_.fullmatch(file_)) and isfile(sep.join([directory_, file_])))
    return [file_id(category_, number_) for number_ in numbers_]


def all_library_files(vocabulary_: Vocabulary) -> List[int | str]:
    return [number_ for category_ in categories_for(vocabulary_) for number_ in library_file_numbers(vocabulary_, category_)]


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
