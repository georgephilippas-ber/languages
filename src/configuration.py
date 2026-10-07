from typing import List

from src.domain import Vocabulary, CEFRLevel

MODEL: str = "gpt-6.1-sol"
FALLBACK_MODELS: List[str] = ["gpt-6.1-sol", "gpt-6-luna", "gpt-6-sol", "gpt-6-astra", "gpt-5.5", "gpt-5.4-mini",
                              "gpt-5.4-nano"]
MODELS_CACHE_SECONDS: int = 3600
MIN_MODEL_GENERATION: int = 5
MAX_MODELS: int = 8

DEFAULT_NUMBER_OF_QUESTIONS: int = 8
DEFAULT_NUMBER_OF_SENTENCES: int = 4
REVISION_QUESTIONS_NUMBER: int = 20
SECONDS_PER_QUESTION: int = 40

DEFAULT_VOCABULARY: Vocabulary = Vocabulary.GERMAN
DEFAULT_CEFR_LEVEL: CEFRLevel = CEFRLevel.B2

LATEST_FILES_NUMBER: int = 2

UNSEEN_ALPHA = 30
