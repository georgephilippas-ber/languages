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
    correct_choice: int  # zero-based
    complete_sentence: str
    english_translation: str


class Vocabulary(Enum):
    ENGLISH = [str(dirname(__file__)), "..", "vocabulary", "english"]
    GERMAN = [str(dirname(__file__)), "..", "vocabulary", "german"]
    FRENCH = [str(dirname(__file__)), "..", "vocabulary", "french"]


class CEFRLevel(Enum):
    A1 = auto()
    A2 = auto()
    B1 = auto()
    B2 = auto()
    C1 = auto()
    C2 = auto()
