from src.domain import Vocabulary, CEFRLevel

DEFAULT_NUMBER_OF_QUESTIONS: int = 4

DEFAULT_VOCABULARY: Vocabulary = Vocabulary.GERMAN
DEFAULT_CEFR_LEVEL: CEFRLevel = CEFRLevel.B2

UNSEEN_ALPHA = 30  # How much larger the selection probability of unseen words is compared to those seen during sampling
