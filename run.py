#!/usr/local/bin/python3

import argparse
from argparse import Namespace
from os.path import isfile
from typing import Dict

from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_CEFR_LEVEL, DEFAULT_VOCABULARY, UNSEEN_ALPHA
from src.domain import Vocabulary, CEFRLevel
from src.parser import get_vocabulary_file_path


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


if __name__ == "__main__":
    command_line_argument_parser = argparse.ArgumentParser(
        description="Multiple choice vocabulary exercises.",
        epilog="examples:\n  %(prog)s\n  %(prog)s 10 -L FR --level C1\n  %(prog)s 5 -f 4",
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
