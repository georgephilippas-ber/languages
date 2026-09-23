import re
from dataclasses import fields
from os.path import sep
from typing import Optional, List, Dict, Tuple
from os import listdir

from .domain import Vocabulary, Entry



def get_vocabulary_file(vocabulary_: Vocabulary) -> str:
    str_list_: List[str] = []

    path_: List[str] = vocabulary_.value

    for i_ in range(len(listdir(sep.join(path_)))):
        filename_ = vocabulary_.name.lower() + "-" + str(i_ + 1) + ".md"
        filename_full_: str = sep.join(path_ + [filename_])

        with open(filename_full_ , "r", encoding="utf-8") as vocabulary_file_:
            str_list_.append(vocabulary_file_.read())

    return "\n".join(str_list_)


def parse_term(term_entry: str) -> Optional[Entry]:
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


def split_vocabulary_text(vocabulary_text_: str) -> List[str]:
    return ["## " + entry_.strip() for entry_ in vocabulary_text_.split("##") if
            entry_.strip() not in [""] and not entry_.strip().startswith("# ")]


def parse_vocabulary(vocabulary_: Vocabulary) -> List[Entry]:
    return [parsed_ for parsed_ in
            [parse_term(entry_) for entry_ in split_vocabulary_text(get_vocabulary_file(vocabulary_))] if
            parsed_ is not None]


def list_to_sampling_dict(entries_: List[Entry]) -> Dict[str, Tuple[Entry, int]]:
    return {entry_.term: (entry_, 0) for index_, entry_ in enumerate(entries_)}


def extract_vocabulary(vocabulary_: Vocabulary) -> Dict[str, Tuple[Entry, int]]:
    return list_to_sampling_dict(parse_vocabulary(vocabulary_))


if __name__ == "__main__":
    print(parse_vocabulary(Vocabulary.GERMAN))
