#!/usr/local/bin/python3

import argparse
from argparse import Namespace

from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_CEFR_LEVEL, DEFAULT_VOCABULARY, UNSEEN_ALPHA
from src.domain import Vocabulary


def positive_integer(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or int(value) <= 0:
        raise argparse.ArgumentTypeError()

    return int(value)


def vocabulary(value: str) -> Vocabulary:
    match value.strip().upper():
        case "ENG":
            return Vocabulary.ENGLISH
        case "DEU":
            return Vocabulary.GERMAN
        case "FR":
            return Vocabulary.FRENCH
        case _:
            raise argparse.ArgumentTypeError()


if __name__ == "__main__":
    command_line_argument_parser = argparse.ArgumentParser()
    command_line_argument_parser.add_argument("vocabulary", nargs="?", default=DEFAULT_VOCABULARY,
                                              type=vocabulary)
    command_line_argument_parser.add_argument("questions_number", nargs="?", default=DEFAULT_NUMBER_OF_QUESTIONS,
                                              type=positive_integer)
    args: Namespace = command_line_argument_parser.parse_args()

    from src.launcher import launch_console
    from src.openai_integration import openai_construct_exercise

    print(launch_console(
        openai_construct_exercise(questions_number=args.questions_number, vocabulary_=args.vocabulary,
                                  cefr_level_=DEFAULT_CEFR_LEVEL, unseen_alpha=UNSEEN_ALPHA)) * 100)
