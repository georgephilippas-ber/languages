import re
from csv import writer, QUOTE_ALL
from os import makedirs
from os.path import dirname, sep
from typing import Dict, List, Optional, Tuple

from src.domain import Vocabulary
from src.parser import get_vocabulary_file_path, get_vocabulary_file_numbers

ANKI_DIRECTORY_PATH_ELEMENTS: List[str] = [dirname(__file__), "..", "..", "vocabulary", "anki"]

# Sections of an entry, in the order they appear on the back of a card. Unlabelled paragraphs (e.g. "Another
# example:", "Useful nuance:") and unknown labels are appended to the section above them.
CARD_SECTIONS: List[str] = ["Definition", "Grammar", "Example", "Synonym", "English", "CEFR"]

LABEL_REGEXP = re.compile(r"^\*\*([A-Za-z ]+):\*\*")
BOLD_REGEXP = re.compile(r"\*\*(.+?)\*\*")
ITALIC_REGEXP = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
BULLET_REGEXP = re.compile(r"^[*-] ")


def markdown_to_html(text_: str) -> str:
    return ITALIC_REGEXP.sub(r"<i>\1</i>", BOLD_REGEXP.sub(r"<b>\1</b>", text_))


def __paragraphs(body_: str) -> List[str]:
    return [" ".join(BULLET_REGEXP.sub("<br>• ", line_.strip()) for line_ in paragraph_.strip().splitlines())
            for paragraph_ in re.split(r"\n\s*\n", body_) if paragraph_.strip()]


def __card(chunk_: str) -> List[str]:
    heading_, _, body_ = chunk_.partition("\n")
    sections_: Dict[str, str] = {}
    last_section_: Optional[str] = None

    for paragraph_ in __paragraphs(body_):
        label_match_ = LABEL_REGEXP.match(paragraph_)
        if label_match_ and label_match_.group(1) in CARD_SECTIONS:
            last_section_ = label_match_.group(1)
            sections_[last_section_] = paragraph_
        elif last_section_ is not None:
            sections_[last_section_] += " " + paragraph_

    back_ = "<br><br>".join(markdown_to_html(sections_[section_]) for section_ in CARD_SECTIONS if section_ in sections_)

    return [heading_.strip(), back_]


def vocabulary_text_to_cards(vocabulary_text_: str) -> List[List[str]]:
    # Anything before the first "## " heading (title, introduction) is not an entry.
    return [__card(chunk_) for chunk_ in re.split(r"^## ", vocabulary_text_, flags=re.M)[1:]]


def get_anki_deck_path(vocabulary_: Vocabulary, file_number_: Optional[int] = None) -> str:
    suffix_ = str(file_number_) if file_number_ is not None else "all"

    return sep.join(ANKI_DIRECTORY_PATH_ELEMENTS + [vocabulary_.name.lower() + "-" + suffix_ + ".csv"])


def create_anki_deck(vocabulary_: Vocabulary, file_number_: Optional[int] = None) -> Tuple[str, int]:
    """Writes the deck for one vocabulary file, or for all of them when no number is given, overwriting any
    existing deck. Returns the deck's path and its number of cards."""
    file_numbers_ = [file_number_] if file_number_ is not None else get_vocabulary_file_numbers(vocabulary_)

    cards_: List[List[str]] = []
    for i_ in file_numbers_:
        with open(get_vocabulary_file_path(vocabulary_, i_), "r", encoding="utf-8") as vocabulary_file_:
            cards_.extend(vocabulary_text_to_cards(vocabulary_file_.read()))

    deck_path_ = get_anki_deck_path(vocabulary_, file_number_)
    makedirs(dirname(deck_path_), exist_ok=True)

    with open(deck_path_, "w", newline="", encoding="utf-8") as deck_file_:
        writer(deck_file_, quoting=QUOTE_ALL).writerows(cards_)

    return deck_path_, len(cards_)


if __name__ == "__main__":
    pass
