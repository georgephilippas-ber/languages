from random import sample

from src.domain import Vocabulary, CEFRLevel
from src.openai_integration import single_writing_exercise
from src.parser import parse_vocabulary_to_list

if __name__ == "__main__":
    population_ = parse_vocabulary_to_list(Vocabulary.GERMAN)
    entries_sample_ = sample(population_, 2)

    single_writing_exercise(entries_sample_, vocabulary=Vocabulary.GERMAN, cefr_level=CEFRLevel.B2)
