from typing import Optional, List
from dataclasses import dataclass, fields
import re

from .domain import Vocabulary, Entry

def get_vocabulary_file(vocabulary_: Vocabulary) -> str:
    with open(vocabulary_.value, "r", encoding="utf-8") as vocabulary_file_:
        return vocabulary_file_.read()


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


if __name__ == "__main__":
    print(parse_vocabulary(Vocabulary.GERMAN))
