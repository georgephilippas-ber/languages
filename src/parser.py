from typing import Optional
from dataclasses import dataclass
import re

example = """
## tadellos / tadellose

**Definition:** Completely without faults, defects, or grounds for criticism; impeccable in quality, behavior, or condition.  
**Grammar:** Adjective. *tadellose* is a declined form of *tadellos*; the ending depends on case, gender, number, and article.  
**Example:** *Sie hat eine tadellose Arbeit geleistet.* — “She did an impeccable job.”  
**English:** **impeccable**

"""


@dataclass
class Entry:
    term: str
    grammar: str
    example: str
    english: str
    french: str
    german: str


def parse(term_entry: str) -> Optional[Entry]:
    lines_ = [line_.strip() for line_ in term_entry.splitlines() if line_.strip() != ""]
    print(lines_)

    line_regexp_ = re.compile(r"^\*\*(Definition|Grammar|Example|English):\*\*\s*(.*)$")

    for line_ in lines_:
        line_match_ = line_regexp_.match(line_)
        print(line_match_)

    return None


if __name__ == "__main__":
    print(parse(example))
