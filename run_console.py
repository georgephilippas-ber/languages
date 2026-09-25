#!/usr/local/bin/python3

import argparse
from argparse import Namespace

from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_CEFR_LEVEL, DEFAULT_VOCABULARY, UNSEEN_ALPHA
from src.domain import Vocabulary, CEFRLevel


def positive_integer(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or int(value) <= 0:
        raise argparse.ArgumentTypeError()

    return int(value)


def vocabulary(value: str) -> Vocabulary:
    try:
        return Vocabulary[value.strip().upper()]
    except KeyError:
        raise argparse.ArgumentTypeError()


def cefr_level(value: str) -> CEFRLevel:
    try:
        return CEFRLevel[value.strip().upper()]
    except KeyError:
        raise argparse.ArgumentTypeError() from None


if __name__ == "__main__":
    command_line_argument_parser = argparse.ArgumentParser()
    command_line_argument_parser.add_argument("vocabulary", nargs="?", default=DEFAULT_VOCABULARY,
                                              type=vocabulary)
    command_line_argument_parser.add_argument("questions_number", nargs="?", default=DEFAULT_NUMBER_OF_QUESTIONS,
                                              type=positive_integer)
    command_line_argument_parser.add_argument("cefr_level", nargs="?", default=DEFAULT_CEFR_LEVEL,
                                              type=cefr_level)
    args: Namespace = command_line_argument_parser.parse_args()

    from src.launcher import launch_console
    from src.openai_integration import openai_construct_exercise

    try:
        print(launch_console(
            openai_construct_exercise(questions_number=args.questions_number, vocabulary_=args.vocabulary,
                                      cefr_level_=args.cefr_level, unseen_alpha=UNSEEN_ALPHA)) * 100)
    except KeyboardInterrupt:
        pass
