from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum, auto
from os import environ
from os.path import dirname, sep

DATA_VARIABLE: str = "LANGUAGES_DATA"
DATA_ROOT: str = environ.get(DATA_VARIABLE) or sep.join([str(dirname(__file__)), ".."])


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
    correct_choice: int
    complete_sentence: str
    english_translation: str
    choices_translations: List[str] = field(default_factory=list)
    term: str = ""


@dataclass
class Correction:
    original: str
    corrected: str
    explanation: str


class Vocabulary(Enum):
    ENGLISH = [DATA_ROOT, "vocabulary", "english"]
    GERMAN = [DATA_ROOT, "vocabulary", "german"]
    FRENCH = [DATA_ROOT, "vocabulary", "french"]


class CEFRLevel(Enum):
    A1 = auto()
    A2 = auto()
    B1 = auto()
    B2 = auto()
    C1 = auto()
    C2 = auto()


BLANK: str = "_____"

LANGUAGE_CODES: Dict[str, Vocabulary] = {"EN": Vocabulary.ENGLISH, "DE": Vocabulary.GERMAN, "FR": Vocabulary.FRENCH}


def language_code(vocabulary_: Vocabulary) -> str:
    return next(code_ for code_, member_ in LANGUAGE_CODES.items() if member_ == vocabulary_)
