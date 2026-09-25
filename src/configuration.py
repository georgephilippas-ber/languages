from src.domain import Vocabulary, CEFRLevel

DEBUG: bool = True

if DEBUG:
    DEFAULT_NUMBER_OF_QUESTIONS: int = 4
else:
    DEFAULT_NUMBER_OF_QUESTIONS: int = 10

DEFAULT_VOCABULARY: Vocabulary = Vocabulary.GERMAN
DEFAULT_CEFR_LEVEL: CEFRLevel = CEFRLevel.C1

UNSEEN_ALPHA = 30  # How much larger the selection probability of unseen words is compared to those seen during sampling
