from typing import List

from src.domain import Entry, Vocabulary
from src.parser import parse_vocabulary

if __name__ == "__main__":
    entries_: List[Entry] = parse_vocabulary(Vocabulary.GERMAN)

    words_ = [word_.term for word_ in entries_]
    print(words_)

    # print(openai_construct_single_multiple_choice_question(entries_[10], ["one", "two"], Vocabulary.GERMAN, CEFRLevel.A2))

