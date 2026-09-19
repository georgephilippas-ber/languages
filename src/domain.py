from dataclasses import dataclass
from typing import Optional, List
from enum import Enum, auto
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
    english_translation: str


class Vocabulary(Enum):
    ENGLISH = sep.join([str(dirname(__file__)), "..", "vocabulary", "english", "english.md"])
    GERMAN = sep.join([str(dirname(__file__)), "..", "vocabulary", "german", "german.md"])
    FRENCH = sep.join([str(dirname(__file__)), "..", "vocabulary", "french", "french.md"])

class CEFRLevel(Enum):
    A1 = auto()
    A2 = auto()
    B1 = auto()
    B2 = auto()
    C1 = auto()
    C2 = auto()
