from src.domain import Vocabulary, CEFRLevel

DEBUG: bool = True

if DEBUG:
    DEFAULT_NUMBER_OF_QUESTIONS = 4
else:
    DEFAULT_NUMBER_OF_QUESTIONS = 10

DEFAULT_VOCABULARY: Vocabulary = Vocabulary.FRENCH
DEFAULT_CEFR_LEVEL: CEFRLevel = CEFRLevel.B2

UNSEEN_ALPHA = 30  # How much larger the selection probability of unseen words is compared to those seen during sampling
