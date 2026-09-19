from typing import Optional
from dataclasses import dataclass, fields
import re

example = """
## tadellos / tadellose

**Definition:** Completely without faults, defects, or grounds for criticism; impeccable in quality, behavior, or condition.  
**Grammar:** Adjective. *tadellose* is a declined form of *tadellos*; the ending depends on case, gender, number, and article.  
**Example:** *Sie hat eine tadellose Arbeit geleistet.* — “She did an impeccable job.”  
**English:** **impeccable**

## tadellos / tadellose

**Definition:** Completely without faults, defects, or grounds for criticism; impeccable in quality, behavior, or condition.  
**Grammar:** Adjective. *tadellose* is a declined form of *tadellos*; the ending depends on case, gender, number, and article.  
**Example:** *Sie hat eine tadellose Arbeit geleistet.* — “She did an impeccable job.”  
**English:** **impeccable**

"""


@dataclass
class Entry:
    term: str
    grammar: Optional[str] = ""
    example: Optional[str] = ""
    english: Optional[str] = ""
    french: Optional[str] = ""
    german: Optional[str] = ""


def parse_term(term_entry: str) -> Optional[Entry]:
    lines_ = [line_.strip() for line_ in term_entry.splitlines() if line_.strip() != ""]
    line_regexp_ = re.compile(r"^\*\*(Definition|Grammar|Example|English):\*\*\s*(.*)$")

    if lines_[0].startswith("##"):
        entry_ = Entry(term=lines_[0].lstrip("##").strip())


        for line_ in lines_:
            line_match_ = line_regexp_.match(line_)
            if line_match_:
                groups_ = line_match_.groups()
                for index_, group_ in enumerate(groups_):

                    if group_.lower().strip() in [f.name for f in fields(Entry)]:
                        setattr(entry_, group_.lower().strip(), groups_[1].lower().strip().replace("*", ""))
        return entry_

    return None

if __name__ == "__main__":
    print(len(example.split("##")))
