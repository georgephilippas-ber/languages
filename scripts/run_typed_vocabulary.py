#!/usr/local/bin/python3

import argparse
import sys
from os.path import abspath, basename, dirname
from shutil import get_terminal_size
from textwrap import fill
from time import perf_counter
from typing import List, Tuple

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from run_vocabulary import positive_integer, vocabulary, cefr_level, file_number_or_all, resolve_file_numbers, \
    REVISE_COMMAND
from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_VOCABULARY, DEFAULT_CEFR_LEVEL, \
    LATEST_FILES_NUMBER, SECONDS_PER_QUESTION, REVISION_QUESTIONS_NUMBER
from src.domain import Vocabulary, CEFRLevel, BLANK, LANGUAGE_CODES, language_code
from src.launcher import time_summary
from src.parser import get_vocabulary_file_numbers
from src.selection import ALL_FILES, LATEST_FILE, describe_file_numbers
from src.typed import TypedQuestion, TypedCorrection, VERDICTS, construct_questions, check_answer

QUIT: str = "q"

USE_COLOURS: bool = sys.stdout.isatty()
BOLD, DIM, GREEN, RED, YELLOW, RESET = ("\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[33m", "\033[0m") \
    if USE_COLOURS else ("", "", "", "", "", "")
ITALIC, ITALIC_OFF = ("\033[3m", "\033[23m") if USE_COLOURS else ("", "")
LABEL_WIDTH: int = 13


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


def __print_question(index_: int, total_: int, question_: TypedQuestion):
    print(__style("─" * __width(), DIM))
    print(__style(f"Question {index_ + 1} of {total_}", BOLD) + __style(f"  ·  {SECONDS_PER_QUESTION} s", DIM))
    print()
    print(fill(question_.question, width=__width()))
    print()
    print(__labelled("Hint", question_.hint))
    print()


def __print_correction(question_: TypedQuestion, answer_: str, correction_: TypedCorrection) -> str:
    verdict_ = correction_.verdict
    corrected_ = correction_.corrected_answer

    if verdict_ == "correct":
        print(__style("✓ Correct!", BOLD, GREEN))
    elif verdict_ == "wrong_form":
        print(__style("~ Right word, wrong form", BOLD, YELLOW))
    else:
        print(__style("✗ Incorrect", BOLD, RED))
    print()

    print(__labelled("Yours", question_.question.replace(BLANK, __italic(answer_)),
                     *(() if verdict_ == "correct" else (DIM,))))
    if verdict_ != "correct":
        print(__labelled("Corrected", __italic(corrected_), GREEN))
    if corrected_.strip() != question_.correct_answer.strip():
        print(__labelled("Expected", __italic(question_.correct_answer)))
    print(__labelled("Sentence", question_.complete_sentence))
    print(__labelled("Translation", question_.english_translation))
    print()

    if correction_.errors and verdict_ != "correct":
        print("  " + __style("Errors", DIM))
        for item_ in correction_.errors:
            print(f"  • {__style(item_.original, RED)} → {__style(item_.corrected, GREEN)}")
            if item_.explanation:
                print(fill(item_.explanation, width=__width(), initial_indent="    ", subsequent_indent="    "))
        print()

    if correction_.comment:
        print(fill(correction_.comment, width=__width()))
        print()

    if correction_.suggestions:
        print("  " + __style("Suggestions", DIM))
        for suggestion_ in correction_.suggestions:
            print(fill(suggestion_, width=__width(), initial_indent="  • ", subsequent_indent="    "))
        print()

    return verdict_


def run_typed_quiz(vocabulary_: Vocabulary, cefr_level_: CEFRLevel, questions_number_: int,
                   file_numbers_: List[int], demo_: bool = False):
    print(f"Constructing {questions_number_} typed question{'s' if questions_number_ != 1 else ''} "
          f"at level {cefr_level_.name} in {vocabulary_.name.capitalize()} using "
          f"{describe_file_numbers(vocabulary_, file_numbers_)}.")
    print()

    questions_ = construct_questions(vocabulary_, cefr_level_, questions_number_, file_numbers_, demo_)
    counts_ = {verdict_: 0 for verdict_ in VERDICTS}
    elapsed_ = 0.0

    for index_, question_ in enumerate(questions_):
        __print_question(index_, len(questions_), question_)
        shown_at_ = perf_counter()

        answer_ = ""
        while not answer_:
            answer_ = " ".join(input(f"Your {vocabulary_.name.capitalize()} answer ({QUIT} to quit): ").split())
        print()
        if answer_.lower() == QUIT:
            break
        elapsed_ += perf_counter() - shown_at_

        print(__style("Checking...", DIM))
        correction_, notice_ = check_answer(vocabulary_, question_, answer_, demo_)
        if notice_:
            print(notice_)
        print()

        counts_[__print_correction(question_, answer_, correction_)] += 1

    answered_ = sum(counts_.values())
    if not questions_:
        print("No questions were generated.")
    elif answered_ == 0:
        print("No questions were answered.")
    else:
        print(__style("─" * __width(), DIM))
        print(__style(f"Score: {counts_['correct']}/{answered_} correct ({counts_['correct'] / answered_:.0%}); "
                      f"{counts_['wrong_form']} right word in the wrong form, {counts_['wrong_word']} incorrect",
                      BOLD))
        print(time_summary(elapsed_, answered_))
    print()


DEMO_HELP: str = "use placeholder questions and corrections instead of the API, and do not record practice history"


def __run(vocabulary_: Vocabulary, cefr_level_: CEFRLevel, questions_number_: int, file_numbers_: List[int],
          demo_: bool):
    try:
        run_typed_quiz(vocabulary_, cefr_level_, questions_number_, file_numbers_, demo_)
    except KeyboardInterrupt:
        print()
        print()
    finally:
        print("Goodbye!")


def revise(command_line_arguments_: List[str]):
    revise_parser_ = argparse.ArgumentParser(
        prog=f"{basename(sys.argv[0])} {REVISE_COMMAND}",
        description=f"Run a typed revision quiz of {REVISION_QUESTIONS_NUMBER} questions drawn from all vocabulary "
                    f"files of a language; type '{QUIT}' at an answer prompt to quit.")
    revise_parser_.add_argument("-L", "--language", dest="vocabulary", default=DEFAULT_VOCABULARY, type=vocabulary,
                                metavar="LANGUAGE",
                                help=f"{', '.join(LANGUAGE_CODES)} (default: {language_code(DEFAULT_VOCABULARY)})")
    revise_parser_.add_argument("-l", "--level", dest="cefr_level", default=DEFAULT_CEFR_LEVEL, type=cefr_level,
                                metavar="LEVEL", help=f"CEFR level (default: {DEFAULT_CEFR_LEVEL.name})")
    revise_parser_.add_argument("--demo", action="store_true", help=DEMO_HELP)
    arguments_ = revise_parser_.parse_args(command_line_arguments_)

    __run(arguments_.vocabulary, arguments_.cefr_level, REVISION_QUESTIONS_NUMBER,
          get_vocabulary_file_numbers(arguments_.vocabulary), arguments_.demo)


EXAMPLES: List[Tuple[str, str]] = [
    ("", f"{DEFAULT_NUMBER_OF_QUESTIONS} {DEFAULT_VOCABULARY.name.capitalize()} questions at "
         f"{DEFAULT_CEFR_LEVEL.name} from the latest two files"),
    ("10 -L FR --level C1", "10 French questions at C1 from the latest two files"),
    ("5 -f 2", "5 German questions from german-2.md"),
    (f"-f {ALL_FILES}", f"{DEFAULT_NUMBER_OF_QUESTIONS} German questions from all files"),
    (REVISE_COMMAND, f"{REVISION_QUESTIONS_NUMBER} German questions from all files"),
    (f"{REVISE_COMMAND} -L FR -l C1", f"{REVISION_QUESTIONS_NUMBER} French questions at C1 from all files"),
    ("--demo", "placeholder questions and corrections, without calling the API or recording history"),
]

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == REVISE_COMMAND:
        revise(sys.argv[2:])
        sys.exit(0)

    command_line_argument_parser_ = argparse.ArgumentParser(
        usage="%(prog)s [-h] [-L LANGUAGE] [-l LEVEL] [-f N] [--demo] [questions_number]\n"
              f"       %(prog)s {REVISE_COMMAND} [-h] [-L LANGUAGE] [-l LEVEL] [--demo]",
        description=fill("Typed vocabulary quiz. Like the multiple choice quiz, but the choices are shown only by "
                         "their meaning, in English (in French for English vocabulary): type the missing word "
                         "yourself, in the form the sentence needs, and get a correction with comments and "
                         f"suggestions. Type '{QUIT}' to quit.", width=90),
        epilog="commands:\n"
               f"  {REVISE_COMMAND} [-L LANGUAGE] [-l LEVEL] [--demo]\n"
               f"      typed revision quiz of {REVISION_QUESTIONS_NUMBER} questions from all files; same -L, -l, and "
               "--demo as the quiz\n\n"
               "examples:\n" +
               "\n".join(f"  %(prog)s {example_:<{max(len(example_) for example_, _ in EXAMPLES)}}  {text_}"
                         for example_, text_ in EXAMPLES),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    command_line_argument_parser_.add_argument("questions_number", nargs="?", default=DEFAULT_NUMBER_OF_QUESTIONS,
                                               type=positive_integer,
                                               help=f"number of questions (default: {DEFAULT_NUMBER_OF_QUESTIONS})")
    command_line_argument_parser_.add_argument("-L", "--language", dest="vocabulary", default=DEFAULT_VOCABULARY,
                                               type=vocabulary, metavar="LANGUAGE",
                                               help=f"{', '.join(LANGUAGE_CODES)} "
                                                    f"(default: {language_code(DEFAULT_VOCABULARY)})")
    command_line_argument_parser_.add_argument("-l", "--level", dest="cefr_level", default=DEFAULT_CEFR_LEVEL,
                                               type=cefr_level, metavar="LEVEL",
                                               help=f"CEFR level (default: {DEFAULT_CEFR_LEVEL.name})")
    command_line_argument_parser_.add_argument("-f", "--file", dest="file_number", default=None,
                                               type=file_number_or_all, metavar="N",
                                               help=f"only use the vocabulary file <language>-N.md; '{LATEST_FILE}' "
                                                    f"for the latest {LATEST_FILES_NUMBER} files, i.e. the highest N "
                                                    f"and N - 1, or '{ALL_FILES}' for all files (default: "
                                                    f"{LATEST_FILE})")
    command_line_argument_parser_.add_argument("--demo", action="store_true", help=DEMO_HELP)
    arguments_ = command_line_argument_parser_.parse_args()
    file_numbers_ = resolve_file_numbers(command_line_argument_parser_, "-f/--file", arguments_.vocabulary,
                                         arguments_.file_number)

    __run(arguments_.vocabulary, arguments_.cefr_level, arguments_.questions_number, file_numbers_, arguments_.demo)
