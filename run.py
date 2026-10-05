#!/usr/local/bin/python3

import argparse
import sys
from argparse import Namespace
from os.path import isfile, normpath, basename
from typing import Dict, List, Tuple

from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_CEFR_LEVEL, DEFAULT_VOCABULARY, UNSEEN_ALPHA
from src.domain import Vocabulary, CEFRLevel
from src.parser import get_vocabulary_file_path, get_vocabulary_file_numbers, count_vocabulary_file_terms


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
        prog=f"run.py {CREATE_ANKI_COMMAND}",
        description="Create an Anki deck (CSV) from a vocabulary file under vocabulary/anki, overwriting any "
                    "existing deck.")
    create_anki_parser_.add_argument("vocabulary", type=vocabulary, metavar="LANGUAGE",
                                     help=", ".join(LANGUAGE_CODES))
    create_anki_parser_.add_argument("file_number", nargs="?", default=None, type=positive_integer, metavar="N",
                                     help="convert only <language>-N.md into <language>-N.csv "
                                          "(default: all files into <language>-all.csv)")
    arguments_: Namespace = create_anki_parser_.parse_args(command_line_arguments_)

    if arguments_.file_number is not None:
        file_path_ = get_vocabulary_file_path(arguments_.vocabulary, arguments_.file_number)
        if not isfile(file_path_):
            create_anki_parser_.error(f"argument N: there is no vocabulary file {file_path_}")

    from src.anki_deck.converter import create_anki_deck

    deck_path_, cards_number_ = create_anki_deck(arguments_.vocabulary, arguments_.file_number)
    print(f"Created {normpath(deck_path_)} ({cards_number_} cards).")


INFO_COMMAND: str = "info"


def info(command_line_arguments_: List[str]):
    info_parser_ = argparse.ArgumentParser(
        prog=f"run.py {INFO_COMMAND}",
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
        print(f"  {file_name_:<{width_}}  {terms_number_:>5} terms")
    print(f"  {'Total':<{width_}}  {sum(terms_numbers_):>5} terms")


COMMANDS = {CREATE_ANKI_COMMAND: create_anki, INFO_COMMAND: info}

EXAMPLES: List[Tuple[str, str]] = [
    ("", f"{DEFAULT_NUMBER_OF_QUESTIONS} {DEFAULT_VOCABULARY.name.capitalize()} questions at "
         f"{DEFAULT_CEFR_LEVEL.name} from all files"),
    ("10 -L FR --level C1", "10 French questions at C1"),
    ("5 -f 4", "5 German questions from german-4.md"),
    (f"{CREATE_ANKI_COMMAND} DE 4", "create vocabulary/anki/german-4.csv"),
    (f"{CREATE_ANKI_COMMAND} DE", "create vocabulary/anki/german-all.csv"),
    (f"{INFO_COMMAND} -l FR", "count the French files and terms"),
]

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in COMMANDS:
        COMMANDS[sys.argv[1]](sys.argv[2:])
        sys.exit(0)

    command_line_argument_parser = argparse.ArgumentParser(
        usage="%(prog)s [-h] [-L LANGUAGE] [-l LEVEL] [-f N] [questions_number]\n"
              f"       %(prog)s {CREATE_ANKI_COMMAND} [-h] LANGUAGE [N]\n"
              f"       %(prog)s {INFO_COMMAND} [-h] [-l LANGUAGE]",
        description="Vocabulary tools. Without a command, runs a multiple choice vocabulary quiz with the options "
                    "below.",
        epilog="commands:\n"
               f"  {CREATE_ANKI_COMMAND} LANGUAGE [N]\n"
               "      create an Anki deck under vocabulary/anki from <language>-N.md, or from all files into\n"
               "      <language>-all.csv when N is omitted; overwrites any existing deck\n"
               f"  {INFO_COMMAND} [-l LANGUAGE]\n"
               "      report the number of vocabulary files and of terms in each file and in total;\n"
               f"      here -l is the language (default: {language_code(DEFAULT_VOCABULARY)})\n"
               "  run '%(prog)s COMMAND --help' for a command's own options\n\n"
               "examples:\n" +
               "\n".join(f"  %(prog)s {example_:<{max(len(example_) for example_, _ in EXAMPLES)}}  {text_}"
                         for example_, text_ in EXAMPLES),
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
    command_line_argument_parser.add_argument("-f", "--file", dest="file_number", default=None, type=positive_integer,
                                              metavar="N", help="only use the vocabulary file <language>-N.md")

    arguments_: Namespace = command_line_argument_parser.parse_args()

    if arguments_.file_number is not None:
        file_path_ = get_vocabulary_file_path(arguments_.vocabulary, arguments_.file_number)
        if not isfile(file_path_):
            command_line_argument_parser.error(f"argument -f/--file: there is no vocabulary file {file_path_}")

    from src.launcher import launch_console
    from src.openai_integration import openai_construct_exercise

    try:
        launch_console(
            openai_construct_exercise(questions_number=arguments_.questions_number,
                                      vocabulary_=arguments_.vocabulary,
                                      cefr_level_=arguments_.cefr_level, unseen_alpha=UNSEEN_ALPHA,
                                      file_number_=arguments_.file_number))
    except KeyboardInterrupt:
        pass
    finally:
        print("Goodbye!")
