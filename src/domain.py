from dataclasses import dataclass
from typing import Optional, List
from enum import Enum, auto
from os import sep
from os.path import dirname


@dataclass
class Entry:
    term: str
    definition: Optional[str] = None
    grammar: Optional[str] = None
    example: Optional[str] = None
    english: Optional[str] = None
    french: Optional[str] = None
    german: Optional[str] = None

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
