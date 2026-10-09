#!/usr/bin/env python3

import re
import sys
from os import environ, makedirs
from os.path import abspath, dirname, isdir, isfile, join
from random import sample
from shutil import copytree, rmtree

DATA: str = dirname(abspath(__file__))
ROOT: str = dirname(DATA)
FACTORY: str = join(DATA, "factory")
TERMS_PER_LANGUAGE: int = 8

environ["LANGUAGES_DATA"] = DATA
sys.path.insert(0, ROOT)

from src.database import DATABASE_PATH_ELEMENTS, create_table, get_database_connection
from src.domain import Vocabulary
from src.library import library_file_name


def __entries(text_: str) -> list:
    return [section_.strip() for section_ in re.split(r"^(?=## )", text_, flags=re.MULTILINE)
            if section_.startswith("## ")]


def __preamble(text_: str) -> str:
    return re.split(r"^## ", text_, maxsplit=1, flags=re.MULTILINE)[0].strip()


def __create_factory_vocabulary(vocabulary_: Vocabulary):
    name_ = vocabulary_.name.lower()
    source_directory_ = join(ROOT, "vocabulary", name_)
    factory_directory_ = join(FACTORY, name_)
    if isdir(factory_directory_):
        return

    file_number_ = 1
    texts_ = []
    while isfile(join(source_directory_, library_file_name(vocabulary_, file_number_))):
        with open(join(source_directory_, library_file_name(vocabulary_, file_number_)), encoding="utf-8") as file_:
            texts_.append(file_.read())
        file_number_ += 1

    unique_ = {}
    for text_ in texts_:
        for entry_ in __entries(text_):
            unique_.setdefault(entry_.splitlines()[0], entry_)
    chosen_ = sample(list(unique_.values()), min(TERMS_PER_LANGUAGE, len(unique_)))

    preamble_ = __preamble(texts_[0]) if texts_ else ""
    makedirs(factory_directory_)
    with open(join(factory_directory_, library_file_name(vocabulary_, 1)), "w", encoding="utf-8") as file_:
        file_.write("\n\n".join(([preamble_] if preamble_ else []) + chosen_) + "\n")
    print(f"Chose {len(chosen_)} {name_} factory terms.")


def __reset_vocabulary():
    vocabulary_directory_ = join(DATA, "vocabulary")
    if isdir(vocabulary_directory_):
        rmtree(vocabulary_directory_)
    copytree(FACTORY, vocabulary_directory_)


def __reset_history():
    makedirs(join(*DATABASE_PATH_ELEMENTS), exist_ok=True)
    connection_ = get_database_connection()
    create_table(connection_)
    connection_.commit()
    connection_.close()


if __name__ == "__main__":
    for vocabulary_ in Vocabulary:
        __create_factory_vocabulary(vocabulary_)
    __reset_vocabulary()
    __reset_history()
    print("Reset the packaged app's data to the factory terms and an empty practice history.")
