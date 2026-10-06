import sys
from shutil import get_terminal_size
from textwrap import fill
from time import perf_counter
from typing import List

from src.configuration import SECONDS_PER_QUESTION
from src.domain import SingleMultipleChoiceQuestion

USE_COLOURS: bool = sys.stdout.isatty()

BOLD, DIM, GREEN, RED, RESET = ("\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[0m") if USE_COLOURS else \
    ("", "", "", "", "")
ITALIC, ITALIC_OFF = ("\033[3m", "\033[23m") if USE_COLOURS else ("", "")

LABEL_WIDTH: int = 13

QUIT: str = "q"


def __style(text_: str, *styles_: str) -> str:
    return "".join(styles_) + text_ + RESET if styles_ and USE_COLOURS else text_


def __italic(text_: str) -> str:
    return ITALIC + text_ + ITALIC_OFF


def __letter(index_: int) -> str:
    return chr(ord('A') + index_)


def __width() -> int:
    return min(get_terminal_size((100, 24)).columns, 100)


def __labelled(label_: str, text_: str) -> str:
    indent_ = " " * (2 + LABEL_WIDTH)
    wrapped_ = fill(text_, width=__width(), initial_indent=indent_, subsequent_indent=indent_)

    return "  " + __style(label_.ljust(LABEL_WIDTH), DIM) + wrapped_[len(indent_):]


def format_duration(seconds_: float) -> str:
    seconds_ = int(round(seconds_))
    return f"{seconds_ // 60}:{seconds_ % 60:02d}"


def time_summary(elapsed_: float, answered_: int) -> str:
    allotted_ = SECONDS_PER_QUESTION * answered_
    difference_ = allotted_ - elapsed_
    balance_ = f"{format_duration(difference_)} under" if difference_ >= 0 else f"{format_duration(-difference_)} over"
    text_ = (f"Time: {format_duration(elapsed_)} of {format_duration(allotted_)} allotted "
             f"({answered_} × {SECONDS_PER_QUESTION} s), {balance_}")

    return __style(text_, BOLD, GREEN if difference_ >= 0 else RED)


def __print_question(index_: int, total_: int, question_: SingleMultipleChoiceQuestion):
    print(__style("─" * __width(), DIM))
    print(__style(f"Question {index_ + 1} of {total_}", BOLD) + __style(f"  ·  {SECONDS_PER_QUESTION} s", DIM))
    print()
    print(fill(question_.question, width=__width()))
    print()

    for choice_index_, choice_ in enumerate(question_.choices):
        print(f"  {__letter(choice_index_)}. {choice_}")
    print()


def __print_feedback(question_: SingleMultipleChoiceQuestion, answer_index_: int):
    correct_index_ = question_.correct_choice

    if answer_index_ == correct_index_:
        print(__style("✓ Correct!", BOLD, GREEN))
    else:
        print(__style(f"✗ Incorrect. The correct answer is {__letter(correct_index_)}: "
                      f"{__italic(question_.choices[correct_index_])}", BOLD, RED))
    print()

    print(__labelled("Sentence", question_.complete_sentence))
    print(__labelled("Translation", question_.english_translation))
    print()

    print("  " + __style("Choices", DIM))
    translations_ = question_.choices_translations
    choice_width_ = max(len(choice_) for choice_ in question_.choices)

    for choice_index_, choice_ in enumerate(question_.choices):
        translation_ = translations_[choice_index_] if choice_index_ < len(translations_) else ""
        padding_ = " " * (choice_width_ - len(choice_))
        line_ = f"{__letter(choice_index_)}  {__italic(choice_)}{padding_}  {translation_}".rstrip()

        if choice_index_ == correct_index_:
            mark_, styles_ = "✓", (GREEN,)
        elif choice_index_ == answer_index_:
            mark_, styles_ = "✗", (RED,)
        else:
            mark_, styles_ = " ", (DIM,)

        suffix_ = "  ← your answer" if choice_index_ == answer_index_ else ""
        print("  " + __style(f"{mark_} {line_}{suffix_}", *styles_))
    print()


def launch_console(questions_: List[SingleMultipleChoiceQuestion]) -> float:
    correct_answers_, answered_ = 0, 0
    elapsed_ = 0.0

    for index_, question_ in enumerate(questions_):
        __print_question(index_, len(questions_), question_)
        shown_at_ = perf_counter()

        valid_answers_ = [__letter(idx_) for idx_ in range(0, len(question_.choices))]
        answer_string_ = ""
        while answer_string_ not in valid_answers_ and answer_string_ != QUIT:
            answer_string_ = input(f"Answer ({'/'.join(valid_answers_)}, or {QUIT} to quit): ").strip().upper()
            answer_string_ = QUIT if answer_string_.lower() == QUIT else answer_string_
        print()

        if answer_string_ == QUIT:
            break

        elapsed_ += perf_counter() - shown_at_
        answered_ += 1
        answer_index_ = ord(answer_string_) - ord('A')
        if answer_index_ == question_.correct_choice:
            correct_answers_ += 1

        __print_feedback(question_, answer_index_)

    if len(questions_) == 0:
        print("No questions were generated.")
    elif answered_ == 0:
        print("No questions were answered.")
    else:
        stopped_early_ = f", stopped after {answered_} of {len(questions_)} questions" \
            if answered_ < len(questions_) else ""
        print(__style("─" * __width(), DIM))
        print(__style(f"Score: {correct_answers_}/{answered_} correct "
                      f"({float(correct_answers_) / answered_:.0%}){stopped_early_}", BOLD))
        print(time_summary(elapsed_, answered_))
    print()

    return float(correct_answers_) / answered_ if answered_ > 0 else -1.0
