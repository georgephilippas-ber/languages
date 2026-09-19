from typing import List

from src.domain import Entry, Vocabulary, CEFRLevel
from src.openai_integration import openai_construct_single_multiple_choice_question
from src.parser import parse_vocabulary

if __name__ == "__main__":
    entries_: List[Entry] = parse_vocabulary(Vocabulary.GERMAN)

    print(openai_construct_single_multiple_choice_question(entries_[10], ["one", "two"], Vocabulary.GERMAN, CEFRLevel.A2))

