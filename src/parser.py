import re
from dataclasses import fields
from os import listdir
from os.path import sep
from typing import Optional, List, Dict, Tuple

try:
    from .domain import Vocabulary, Entry, CEFRLevel
    from .openai_prompt import writing_question_prompt
except (ImportError, ModuleNotFoundError):
    from domain import Vocabulary, Entry, CEFRLevel
    from openai_prompt import writing_question_prompt


def get_vocabulary_file_path(vocabulary_: Vocabulary, file_number_: int) -> str:
    return sep.join(vocabulary_.value + [vocabulary_.name.lower() + "-" + str(file_number_) + ".md"])


def get_vocabulary_file_numbers(vocabulary_: Vocabulary) -> List[int]:
    return list(range(1, len([file_ for file_ in listdir(sep.join(vocabulary_.value)) if file_.endswith(".md")]) + 1))


def count_vocabulary_file_terms(vocabulary_: Vocabulary, file_number_: int) -> int:
    with open(get_vocabulary_file_path(vocabulary_, file_number_), "r", encoding="utf-8") as vocabulary_file_:
        return len(re.findall(r"^## ", vocabulary_file_.read(), flags=re.M))


def get_vocabulary_file(vocabulary_: Vocabulary, file_number_: Optional[int] = None) -> str:
    str_list_: List[str] = []

    file_numbers_ = [file_number_] if file_number_ is not None else get_vocabulary_file_numbers(vocabulary_)

    for i_ in file_numbers_:
        with open(get_vocabulary_file_path(vocabulary_, i_), "r", encoding="utf-8") as vocabulary_file_:
            str_list_.append(vocabulary_file_.read())

    return "\n".join(str_list_)


def __parse_term(term_entry: str) -> Optional[Entry]:
    lines_ = [line_.strip() for line_ in term_entry.splitlines() if line_.strip() != ""]

    if not lines_:
        return None

    line_regexp_ = re.compile(r"^\*\*(Definition|Grammar|Example|English):\*\*\s*(.*)$")

    if lines_[0].startswith("##"):
        entry_ = Entry(term=lines_[0].lstrip("##").strip())

        for line_ in lines_:
            line_match_ = line_regexp_.match(line_)
            if line_match_:
                groups_ = line_match_.groups()
                for index_, group_ in enumerate(groups_):
                    if group_.lower().strip() in [field_.name for field_ in fields(Entry)]:
                        setattr(entry_, group_.lower().strip(), groups_[1].strip().replace("*", ""))
        return entry_

    return None


def __split_vocabulary_text(vocabulary_text_: str) -> List[str]:
    return ["## " + entry_.strip() for entry_ in vocabulary_text_.split("##") if
            entry_.strip() not in [""] and not entry_.strip().startswith("# ")]


def __list_to_sampling_dict(entries_: List[Entry]) -> Dict[str, Tuple[Entry, int]]:
    return {entry_.term: (entry_, 0) for index_, entry_ in enumerate(entries_)}


def parse_vocabulary_to_list(vocabulary_: Vocabulary, file_number_: Optional[int] = None) -> List[Entry]:
    return [parsed_ for parsed_ in
            [__parse_term(entry_) for entry_ in
             __split_vocabulary_text(get_vocabulary_file(vocabulary_, file_number_))] if
            parsed_ is not None]


def parse_vocabulary_to_dict(vocabulary_: Vocabulary, file_number_: Optional[int] = None) -> Dict[
    str, Tuple[Entry, int]]:
    return __list_to_sampling_dict(parse_vocabulary_to_list(vocabulary_, file_number_))


if __name__ == "__main__":
    pass
