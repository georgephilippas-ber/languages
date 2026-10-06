#!/usr/local/bin/python3

import argparse
import sys
from os.path import abspath, dirname
from shutil import get_terminal_size
from textwrap import fill
from typing import List, Optional, Sequence, Tuple

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from run_vocabulary import positive_integer, vocabulary, file_number_or_all, resolve_file_numbers
from src.configuration import DEFAULT_NUMBER_OF_SENTENCES, DEFAULT_VOCABULARY, LATEST_FILES_NUMBER
from src.domain import Vocabulary, LANGUAGE_CODES, language_code
from src.parser import get_vocabulary_file_numbers
from src.selection import ALL_FILES, LATEST_FILE, describe_file_numbers
from src.writing import IndexedTerm, WritingCorrection, WORDS_PER_SENTENCE, index_vocabulary, pick_word_pairs, \
    check_sentence

QUIT: str = "quit"

USE_COLOURS: bool = sys.stdout.isatty()
BOLD, DIM, GREEN, RED, YELLOW, RESET = ("\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[33m", "\033[0m") \
    if USE_COLOURS else ("", "", "", "", "", "")
ITALIC, ITALIC_OFF = ("\033[3m", "\033[23m") if USE_COLOURS else ("", "")
LABEL_WIDTH: int = 13
HINT_COLUMN_LIMIT: int = 40


def __style(text_: str, *styles_: str) -> str:
    return "".join(styles_) + text_ + RESET if styles_ and USE_COLOURS else text_


def __italic(text_: str) -> str:
    return ITALIC + text_ + ITALIC_OFF


def __width() -> int:
    return min(get_terminal_size((100, 24)).columns, 100)


def __labelled(label_: str, text_: str, *styles_: str) -> str:
    indent_ = " " * (2 + LABEL_WIDTH)
    wrapped_ = fill(text_, width=__width(), initial_indent=indent_, subsequent_indent=indent_)[len(indent_):]

    return "  " + __style(label_.ljust(LABEL_WIDTH), DIM) + __style(wrapped_, *styles_)


def __print_task(round_: int, rounds_: int, vocabulary_: Vocabulary, terms_: Sequence[IndexedTerm]):
    print(__style("─" * __width(), DIM))
    print(__style(f"Sentence {round_} of {rounds_}", BOLD))
    print()
    print(f"Write one sentence in {vocabulary_.name.capitalize()} that uses both of these words:")
    print()
    term_width_ = max(len(term_.term) for term_ in terms_)
    for term_ in terms_:
        if term_width_ <= HINT_COLUMN_LIMIT:
            padding_ = " " * (term_width_ - len(term_.term))
            print(f"  • {__italic(term_.term)}{padding_}  {__style(term_.hint, DIM)}".rstrip())
        else:
            print(f"  • {__italic(term_.term)}")
            if term_.hint:
                print("    " + __style(term_.hint, DIM))
    print()


def __print_correction(sentence_: str, correction_: WritingCorrection, terms_: Sequence[IndexedTerm]) -> bool:
    minimal_ = correction_.minimal_correction
    natural_ = correction_.natural_version
    is_correct_ = correction_.is_correct

    print(__style("✓ Correct!", BOLD, GREEN) if is_correct_ else __style("✎ Corrected", BOLD, YELLOW))
    print()
    if is_correct_:
        print(__labelled("Yours", sentence_))
    else:
        print(__labelled("Yours", sentence_, DIM))
        print(__labelled("Minimal fix", minimal_))
    if natural_.strip() != minimal_.strip():
        print(__labelled("Natural", natural_, GREEN))
    else:
        print(__labelled("Natural", "(already natural)", DIM))
    print(__labelled("Translation", correction_.translation))
    print()

    term_width_ = max(len(term_.term) for term_ in terms_)
    print("  " + __style("Words", DIM))
    for term_, check_ in zip(terms_, correction_.terms):
        used_, used_correctly_ = check_.used, check_.used_correctly

        if used_ and used_correctly_:
            mark_, status_, styles_ = "✓", "used correctly", (GREEN,)
        elif used_:
            mark_, status_, styles_ = "~", "used, but not quite right", (YELLOW,)
        else:
            mark_, status_, styles_ = "✗", "not used", (RED,)

        if term_width_ <= HINT_COLUMN_LIMIT:
            padding_ = " " * (term_width_ - len(term_.term))
            print("  " + __style(f"{mark_} {__italic(term_.term)}{padding_}  {status_}", *styles_))
            indent_ = " " * (6 + term_width_)
        else:
            print("  " + __style(f"{mark_} {__italic(term_.term)}", *styles_))
            print("    " + __style(status_, *styles_))
            indent_ = " " * 4
        if check_.comment and not (used_ and used_correctly_):
            print(fill(check_.comment, width=__width(), initial_indent=indent_, subsequent_indent=indent_))
    print()

    if correction_.corrections and not is_correct_:
        print("  " + __style("Corrections", DIM))
        for item_ in correction_.corrections:
            print(f"  • {__style(item_.original, RED)} → {__style(item_.corrected, GREEN)}")
            if item_.explanation:
                print(fill(item_.explanation, width=__width(), initial_indent="    ", subsequent_indent="    "))
        print()

    if correction_.natural_explanation and natural_.strip() != minimal_.strip():
        print("  " + __style("Why the natural version", DIM))
        print(fill(correction_.natural_explanation, width=__width(), initial_indent="    ", subsequent_indent="    "))
        print()

    if correction_.feedback:
        print(fill(correction_.feedback, width=__width()))
        print()

    return is_correct_


def writing_exercise(vocabulary_: Vocabulary, rounds_: int, file_numbers_: Optional[List[int]] = None):
    index_ = index_vocabulary(vocabulary_, file_numbers_)
    if len(index_) < WORDS_PER_SENTENCE:
        print(f"Not enough {vocabulary_.name.capitalize()} terms for this exercise.")
        return

    word_pairs_ = pick_word_pairs(index_, rounds_)
    file_numbers_ = file_numbers_ if file_numbers_ is not None else get_vocabulary_file_numbers(vocabulary_)
    source_ = describe_file_numbers(vocabulary_, file_numbers_)
    print(f"Picking words from {len(index_)} {vocabulary_.name.capitalize()} term{'s' if len(index_) != 1 else ''} "
          f"in {source_}. Type '{QUIT}' to stop, or press Enter to skip a sentence.")
    print()

    correct_, answered_ = 0, 0

    for round_, terms_ in enumerate(word_pairs_, start=1):
        __print_task(round_, len(word_pairs_), vocabulary_, terms_)

        sentence_ = input("Your sentence: ").strip()
        print()
        if sentence_.lower() == QUIT:
            break
        if not sentence_:
            print(__style("Skipped.", DIM))
            print()
            continue

        print(__style("Correcting...", DIM))
        correction_, notice_ = check_sentence(vocabulary_, terms_, sentence_)
        if correction_ is None:
            print(notice_)
            print()
            continue
        print()

        answered_ += 1
        correct_ += __print_correction(sentence_, correction_, terms_)

    if answered_ > 0:
        print(__style("─" * __width(), DIM))
        print(__style(f"Correct as written: {correct_}/{answered_} sentence{'s' if answered_ != 1 else ''}", BOLD))
        print()


EXAMPLES: List[Tuple[str, str]] = [
    ("", f"{DEFAULT_NUMBER_OF_SENTENCES} sentences in {DEFAULT_VOCABULARY.name.capitalize()}, words from the latest "
         f"two files"),
    ("2 -L FR", "2 sentences in French, words from the latest two files"),
    ("-f 2", f"{DEFAULT_NUMBER_OF_SENTENCES} sentences with words from german-2.md"),
    (f"6 -f {ALL_FILES}", "6 sentences with words from all German files"),
]

if __name__ == "__main__":
    command_line_argument_parser_ = argparse.ArgumentParser(
        description=fill("Sentence-writing exercise. Each round picks two terms from a language's vocabulary "
                         "files (by default the latest two); you write one sentence that uses both, and you get a "
                         "minimal fix of your errors, a natural version as a native speaker would say it, a "
                         "translation, and a check of each term. Press Enter to skip a sentence, or type 'quit' to "
                         "stop.", width=90),
        epilog="examples:\n" +
               "\n".join(f"  %(prog)s {example_:<{max(len(example_) for example_, _ in EXAMPLES)}}  {text_}"
                         for example_, text_ in EXAMPLES) +
               "\n\nfor the multiple choice quiz, Anki decks, and vocabulary info, see "
               "'./scripts/run_vocabulary.py --help'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    command_line_argument_parser_.add_argument("questions_number", nargs="?", default=DEFAULT_NUMBER_OF_SENTENCES,
                                               type=positive_integer,
                                               help=f"number of sentences (default: {DEFAULT_NUMBER_OF_SENTENCES})")
    command_line_argument_parser_.add_argument("-L", "--language", dest="vocabulary", default=DEFAULT_VOCABULARY,
                                               type=vocabulary, metavar="LANGUAGE",
                                               help=f"{', '.join(LANGUAGE_CODES)} "
                                                    f"(default: {language_code(DEFAULT_VOCABULARY)})")
    command_line_argument_parser_.add_argument("-f", "--file", dest="file_number", default=None,
                                               type=file_number_or_all, metavar="N",
                                               help=f"only use words from the vocabulary file <language>-N.md; "
                                                    f"'{LATEST_FILE}' for the latest {LATEST_FILES_NUMBER} files, "
                                                    f"i.e. the highest N and N - 1, or '{ALL_FILES}' for all files "
                                                    f"(default: {LATEST_FILE})")
    arguments_ = command_line_argument_parser_.parse_args()
    file_numbers_ = resolve_file_numbers(command_line_argument_parser_, "-f/--file", arguments_.vocabulary,
                                         arguments_.file_number)

    try:
        writing_exercise(arguments_.vocabulary, arguments_.questions_number, file_numbers_)
    except KeyboardInterrupt:
        print()
        print()
    finally:
        print("Goodbye!")
