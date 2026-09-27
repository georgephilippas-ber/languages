#!/usr/local/bin/python3

import argparse
from argparse import Namespace
from json import loads

from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_CEFR_LEVEL, DEFAULT_VOCABULARY, UNSEEN_ALPHA, DEBUG
from src.domain import Vocabulary, CEFRLevel
from src.openai_prompt import writing_question_prompt
from src.parser import parse_vocabulary_to_list
from src.openai_integration import get_openai_client


def positive_integer(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or int(value) < 0:
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
    if DEBUG:
        client_ = get_openai_client()

        prompt_ = writing_question_prompt(parse_vocabulary_to_list(Vocabulary.GERMAN)[1:4], CEFRLevel.B1)

        openai_response_ = client_.responses.create(
            model="gpt-6-sol",
            input=prompt_,
        )

        response_json_ = loads(openai_response_.output_text)
        print(response_json_)
    else:
        command_line_argument_parser = argparse.ArgumentParser()
        command_line_argument_parser.add_argument("vocabulary", nargs="?", default=DEFAULT_VOCABULARY,
                                                  type=vocabulary)
        command_line_argument_parser.add_argument("questions_number", nargs="?", default=DEFAULT_NUMBER_OF_QUESTIONS,
                                                  type=positive_integer)
        command_line_argument_parser.add_argument("cefr_level", nargs="?", default=DEFAULT_CEFR_LEVEL,
                                                  type=cefr_level)
        arguments_: Namespace = command_line_argument_parser.parse_args()

        from src.launcher import launch_console
        from src.openai_integration import openai_construct_exercise, get_openai_client

        try:
            print(launch_console(
                openai_construct_exercise(questions_number=arguments_.questions_number,
                                          vocabulary_=arguments_.vocabulary,
                                          cefr_level_=arguments_.cefr_level, unseen_alpha=UNSEEN_ALPHA)) * 100)
        except KeyboardInterrupt:
            pass
        finally:
            print("Goodbye!")
