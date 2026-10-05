#!/usr/local/bin/python3

import argparse
import sys
from argparse import Namespace
from os.path import isfile, basename, abspath, dirname
from typing import Dict, List, Tuple, Optional

from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_CEFR_LEVEL, DEFAULT_VOCABULARY, UNSEEN_ALPHA
from src.domain import Vocabulary, CEFRLevel
from src.parser import get_vocabulary_file_path, get_vocabulary_file_numbers, count_vocabulary_file_terms


ALL_FILES: str = "all"
LATEST_FILE: str = "latest"


def file_number_or_all(value: str) -> int | str:
    if value.strip().lower() in (ALL_FILES, LATEST_FILE):
        return value.strip().lower()
    try:
        return positive_integer(value)
    except argparse.ArgumentTypeError:
        raise argparse.ArgumentTypeError(
            f"'{value}' is neither a positive integer nor '{LATEST_FILE}' or '{ALL_FILES}'") from None


def file_number_or_all_or_error(parser_: argparse.ArgumentParser, value: str) -> int | str:
    try:
        return file_number_or_all(value)
    except argparse.ArgumentTypeError:
        parser_.error(f"argument LANGUAGE: '{value}' is not one of {', '.join(LANGUAGE_CODES)}")


def resolve_file_number(parser_: argparse.ArgumentParser, argument_name_: str, vocabulary_: Vocabulary,
                        file_number_: int | str | None) -> Optional[int]:
    """None (not given) and 'latest' become the latest file, 'all' becomes None (all files); a number must name an
    existing file."""
    if file_number_ is None or file_number_ == LATEST_FILE:
        return max(get_vocabulary_file_numbers(vocabulary_))
    if file_number_ == ALL_FILES:
        return None

    file_path_ = get_vocabulary_file_path(vocabulary_, file_number_)
    if not isfile(file_path_):
        parser_.error(f"argument {argument_name_}: there is no vocabulary file {file_path_}")

    return file_number_


def positive_integer(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or int(value) <= 0:
        raise argparse.ArgumentTypeError(f"'{value}' is not a positive integer")

    return int(value)


LANGUAGE_CODES: Dict[str, Vocabulary] = {"EN": Vocabulary.ENGLISH, "DE": Vocabulary.GERMAN, "FR": Vocabulary.FRENCH}


def language_code(vocabulary_: Vocabulary) -> str:
    return next(code_ for code_, member_ in LANGUAGE_CODES.items() if member_ == vocabulary_)


def vocabulary(value: str) -> Vocabulary:
    try:
        return LANGUAGE_CODES[value.strip().upper()]
    except KeyError:
        raise argparse.ArgumentTypeError(f"'{value}' is not one of {', '.join(LANGUAGE_CODES)}") from None


def cefr_level(value: str) -> CEFRLevel:
    try:
        return CEFRLevel[value.strip().upper()]
    except KeyError:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not one of {', '.join(member_.name for member_ in CEFRLevel)}") from None


CREATE_ANKI_COMMAND: str = "create_anki"


def create_anki(command_line_arguments_: List[str]):
    create_anki_parser_ = argparse.ArgumentParser(
        prog=f"{basename(sys.argv[0])} {CREATE_ANKI_COMMAND}",
        description="Create an Anki deck (CSV) from a vocabulary file under vocabulary/anki/<language>, named "
                    "after the file and today's date; a deck created from the same file(s) on the same day is "
                    "overwritten.")
    create_anki_parser_.add_argument("vocabulary", nargs="?", default=None, metavar="LANGUAGE",
                                     help=f"{', '.join(LANGUAGE_CODES)} (default: {language_code(DEFAULT_VOCABULARY)})")
    create_anki_parser_.add_argument("file_number", nargs="?", default=None, type=file_number_or_all, metavar="N",
                                     help=f"convert only <language>-N.md into <language>-N-<date>.csv, or "
                                          f"'{ALL_FILES}' to combine all files into <language>-all-<date>.csv, or "
                                          f"'{LATEST_FILE}' for the latest file, i.e. the highest N (default: "
                                          f"{LATEST_FILE})")
    arguments_: Namespace = create_anki_parser_.parse_args(command_line_arguments_)

    # The language may be left out, e.g. 'create_anki 4', 'create_anki latest' or 'create_anki all'.
    if arguments_.vocabulary is not None and arguments_.vocabulary.strip().upper() not in LANGUAGE_CODES and \
            arguments_.file_number is None:
        arguments_.file_number = file_number_or_all_or_error(create_anki_parser_, arguments_.vocabulary)
        arguments_.vocabulary = None

    try:
        vocabulary_ = vocabulary(arguments_.vocabulary) if arguments_.vocabulary is not None else DEFAULT_VOCABULARY
    except argparse.ArgumentTypeError as error_:
        create_anki_parser_.error(f"argument LANGUAGE: {error_}")

    file_number_ = resolve_file_number(create_anki_parser_, "N", vocabulary_, arguments_.file_number)

    from src.anki_deck.converter import create_anki_deck

    deck_path_, cards_number_ = create_anki_deck(vocabulary_, file_number_)
    deck_path_ = abspath(deck_path_)
    print(f"Created an Anki deck with {cards_number_} cards.")
    print(f"  File name: {basename(deck_path_)}")
    print(f"  Folder:    {dirname(deck_path_)}")
    print(f"  Full path: {deck_path_}")


INFO_COMMAND: str = "info"


def info(command_line_arguments_: List[str]):
    info_parser_ = argparse.ArgumentParser(
        prog=f"{basename(sys.argv[0])} {INFO_COMMAND}",
        description="Report the number of vocabulary files of a language and the number of terms in each of them.")
    info_parser_.add_argument("-l", "--language", dest="vocabulary", default=DEFAULT_VOCABULARY, type=vocabulary,
                              metavar="LANGUAGE",
                              help=f"{', '.join(LANGUAGE_CODES)} (default: {language_code(DEFAULT_VOCABULARY)})")
    arguments_: Namespace = info_parser_.parse_args(command_line_arguments_)

    file_numbers_ = get_vocabulary_file_numbers(arguments_.vocabulary)
    terms_numbers_ = [count_vocabulary_file_terms(arguments_.vocabulary, i_) for i_ in file_numbers_]
    file_names_ = [basename(get_vocabulary_file_path(arguments_.vocabulary, i_)) for i_ in file_numbers_]
    width_ = max([len(name_) for name_ in file_names_] + [len("Total")])

    print(f"{arguments_.vocabulary.name.capitalize()}: {len(file_numbers_)} file{'s' if len(file_numbers_) != 1 else ''}")
    print()
    for file_name_, terms_number_ in zip(file_names_, terms_numbers_):
        print(f"  {file_name_:<{width_}}  {terms_number_:>5} term{'s' if terms_number_ != 1 else ''}")
    print(f"  {'Total':<{width_}}  {sum(terms_numbers_):>5} terms")


def run_quiz(vocabulary_: Vocabulary, cefr_level_: CEFRLevel, questions_number_: int,
             file_number_: Optional[int]):
    """Run the multiple choice quiz; a file number of None draws from all files."""
    if file_number_ is not None:
        source_ = basename(get_vocabulary_file_path(vocabulary_, file_number_))
    else:
        source_ = "all files (" + ", ".join(basename(get_vocabulary_file_path(vocabulary_, i_))
                                          for i_ in get_vocabulary_file_numbers(vocabulary_)) + ")"
    print(f"Constructing {questions_number_} question{'s' if questions_number_ != 1 else ''} "
          f"at level {cefr_level_.name} in {vocabulary_.name.capitalize()} using {source_}.")
    print()

    from src.launcher import launch_console
    from src.openai_integration import openai_construct_exercise

    try:
        launch_console(
            openai_construct_exercise(questions_number=questions_number_,
                                      vocabulary_=vocabulary_,
                                      cefr_level_=cefr_level_, unseen_alpha=UNSEEN_ALPHA,
                                      file_number_=file_number_))
    except KeyboardInterrupt:
        # Ctrl+C leaves the cursor after "^C" on the current line: end that line, then leave an empty one.
        print()
        print()
    finally:
        print("Goodbye!")


REVISE_COMMAND: str = "revise"
REVISION_QUESTIONS_NUMBER: int = 20


def revise(command_line_arguments_: List[str]):
    revise_parser_ = argparse.ArgumentParser(
        prog=f"{basename(sys.argv[0])} {REVISE_COMMAND}",
        description=f"Run a revision quiz of {REVISION_QUESTIONS_NUMBER} multiple choice questions drawn from all "
                    f"vocabulary files of a language; type 'q' at an answer prompt to quit.")
    revise_parser_.add_argument("-L", "--language", dest="vocabulary", default=DEFAULT_VOCABULARY, type=vocabulary,
                                metavar="LANGUAGE",
                                help=f"{', '.join(LANGUAGE_CODES)} (default: {language_code(DEFAULT_VOCABULARY)})")
    revise_parser_.add_argument("-l", "--level", dest="cefr_level", default=DEFAULT_CEFR_LEVEL, type=cefr_level,
                                metavar="LEVEL", help=f"CEFR level (default: {DEFAULT_CEFR_LEVEL.name})")
    arguments_: Namespace = revise_parser_.parse_args(command_line_arguments_)

    run_quiz(arguments_.vocabulary, arguments_.cefr_level, REVISION_QUESTIONS_NUMBER, None)


COMMANDS = {CREATE_ANKI_COMMAND: create_anki, INFO_COMMAND: info, REVISE_COMMAND: revise}

EXAMPLES: List[Tuple[str, str]] = [
    ("", f"{DEFAULT_NUMBER_OF_QUESTIONS} {DEFAULT_VOCABULARY.name.capitalize()} questions at "
         f"{DEFAULT_CEFR_LEVEL.name} from the latest file"),
    ("10 -L FR --level C1", "10 French questions at C1 from the latest file"),
    ("5 -f 2", "5 German questions from german-2.md"),
    (f"-f {LATEST_FILE}", f"{DEFAULT_NUMBER_OF_QUESTIONS} German questions from the latest file (same as no -f)"),
    (f"-f {ALL_FILES}", f"{DEFAULT_NUMBER_OF_QUESTIONS} German questions from all files"),
    (f"{REVISE_COMMAND}", f"{REVISION_QUESTIONS_NUMBER} German questions from all files"),
    (f"{REVISE_COMMAND} -L FR -l C1", f"{REVISION_QUESTIONS_NUMBER} French questions at C1 from all files"),
    (f"{CREATE_ANKI_COMMAND}", "create a deck from the latest German file"),
    (f"{CREATE_ANKI_COMMAND} DE 2", "create vocabulary/anki/german/german-2-<date>.csv"),
    (f"{CREATE_ANKI_COMMAND} FR {ALL_FILES}", "create vocabulary/anki/french/french-all-<date>.csv"),
    (f"{INFO_COMMAND} -l FR", "count the French files and terms"),
]

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in COMMANDS:
        COMMANDS[sys.argv[1]](sys.argv[2:])
        sys.exit(0)

    command_line_argument_parser = argparse.ArgumentParser(
        usage="%(prog)s [-h] [-L LANGUAGE] [-l LEVEL] [-f N] [questions_number]\n"
              f"       %(prog)s {REVISE_COMMAND} [-h] [-L LANGUAGE] [-l LEVEL]\n"
              f"       %(prog)s {CREATE_ANKI_COMMAND} [-h] [LANGUAGE] [N]\n"
              f"       %(prog)s {INFO_COMMAND} [-h] [-l LANGUAGE]",
        description="Vocabulary tools. Without a command, runs a multiple choice vocabulary quiz with the options\n"
                    "below; type 'q' at an answer prompt to quit.",
        epilog="commands:\n"
               f"  {REVISE_COMMAND} [-L LANGUAGE] [-l LEVEL]\n"
               f"      revision quiz of {REVISION_QUESTIONS_NUMBER} questions from all files; same -L and -l as the "
               "quiz\n"
               f"  {CREATE_ANKI_COMMAND} [LANGUAGE] [N]\n"
               "      create an Anki deck under vocabulary/anki/<language> from <language>-N.md, named\n"
               f"      <language>-N-<date>.csv; N = {ALL_FILES} combines all files into <language>-all-<date>.csv\n"
               f"      and N = {LATEST_FILE} uses the latest file; defaults: {language_code(DEFAULT_VOCABULARY)} and "
               f"{LATEST_FILE}; <date> is today\n"
               "      (YYYY-MM-DD), and a deck created again on the same day is overwritten\n"
               f"  {INFO_COMMAND} [-l LANGUAGE]\n"
               "      report the number of vocabulary files and of terms in each file and in total;\n"
               f"      here -l is the language (default: {language_code(DEFAULT_VOCABULARY)})\n"
               "  run '%(prog)s COMMAND --help' for a command's own options\n\n"
               "examples:\n" +
               "\n".join(f"  %(prog)s {example_:<{max(len(example_) for example_, _ in EXAMPLES)}}  {text_}"
                         for example_, text_ in EXAMPLES) +
               "\n\nfor the sentence-writing exercise, see './run_writing.py --help'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    command_line_argument_parser.add_argument("questions_number", nargs="?", default=DEFAULT_NUMBER_OF_QUESTIONS,
                                              type=positive_integer,
                                              help=f"number of questions (default: {DEFAULT_NUMBER_OF_QUESTIONS})")
    command_line_argument_parser.add_argument("-L", "--language", dest="vocabulary", default=DEFAULT_VOCABULARY,
                                              type=vocabulary, metavar="LANGUAGE",
                                              help=f"{', '.join(LANGUAGE_CODES)} "
                                                   f"(default: {language_code(DEFAULT_VOCABULARY)})")
    command_line_argument_parser.add_argument("-l", "--level", dest="cefr_level", default=DEFAULT_CEFR_LEVEL,
                                              type=cefr_level, metavar="LEVEL",
                                              help=f"CEFR level (default: {DEFAULT_CEFR_LEVEL.name})")
    command_line_argument_parser.add_argument("-f", "--file", dest="file_number", default=None,
                                              type=file_number_or_all, metavar="N",
                                              help=f"only use the vocabulary file <language>-N.md; '{LATEST_FILE}' "
                                                   f"for the latest file, i.e. the highest N, or '{ALL_FILES}' for "
                                                   f"all files (default: {LATEST_FILE})")

    arguments_: Namespace = command_line_argument_parser.parse_args()

    arguments_.file_number = resolve_file_number(command_line_argument_parser, "-f/--file", arguments_.vocabulary,
                                                 arguments_.file_number)

    run_quiz(arguments_.vocabulary, arguments_.cefr_level, arguments_.questions_number, arguments_.file_number)
