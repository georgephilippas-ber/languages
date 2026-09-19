from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from os import sep
from os.path import dirname


@dataclass
class Entry:
    term: str
    grammar: Optional[str] = ""
    example: Optional[str] = ""
    english: Optional[str] = ""
    french: Optional[str] = ""
    german: Optional[str] = ""

@dataclass
class SingleMultipleChoiceQuestion:
    question: str
    choices: List[str]
    correct_choice: int # zero-based


class Vocabulary(Enum):
    ENGLISH = sep.join([str(dirname(__file__)), "..", "vocabulary", "english", "english.md"])
    GERMAN = sep.join([str(dirname(__file__)), "..", "vocabulary", "german", "german.md"])
    FRENCH = sep.join([str(dirname(__file__)), "..", "vocabulary", "french", "french.md"])

class CEFRLevel(Enum):
    B2 = 0
    C1 = 1
    C2 = 2