import sys
from shutil import get_terminal_size
from textwrap import fill
from typing import List

from src.domain import SingleMultipleChoiceQuestion

# ANSI styles, only used when printing to a terminal (not when the output is piped or redirected).
USE_COLOURS: bool = sys.stdout.isatty()

BOLD, DIM, GREEN, RED, RESET = ("\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[0m") if USE_COLOURS else \
    ("", "", "", "", "")
# Italic is switched off with its own code (23) rather than RESET, so any surrounding style (e.g. bold red) stays on.
ITALIC, ITALIC_OFF = ("\033[3m", "\033[23m") if USE_COLOURS else ("", "")

LABEL_WIDTH: int = 13  # "Translation  "

QUIT: str = "quit"  # typed at an answer prompt, ends the quiz


def __style(text_: str, *styles_: str) -> str:
    return "".join(styles_) + text_ + RESET if styles_ and USE_COLOURS else text_


def __italic(text_: str) -> str:
    """For the words of the language being learned; safe to use inside a styled line."""
    return ITALIC + text_ + ITALIC_OFF


def __letter(index_: int) -> str:
    return chr(ord('A') + index_)


def __width() -> int:
    return min(get_terminal_size((100, 24)).columns, 100)


def __labelled(label_: str, text_: str) -> str:
    """e.g. 'Translation  The troops advanced …', wrapping long text under itself rather than under the label."""
    indent_ = " " * (2 + LABEL_WIDTH)
    wrapped_ = fill(text_, width=__width(), initial_indent=indent_, subsequent_indent=indent_)

    return "  " + __style(label_.ljust(LABEL_WIDTH), DIM) + wrapped_[len(indent_):]


def __print_question(index_: int, total_: int, question_: SingleMultipleChoiceQuestion):
    print(__style("─" * __width(), DIM))
    print(__style(f"Question {index_ + 1} of {total_}", BOLD))
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
        # Pad outside the italic codes, which take no space on screen but would count towards ljust.
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
    """Returns the share of correctly answered questions among those answered, or -1.0 if none were answered.
    Typing 'quit' at an answer prompt ends the quiz early."""
    correct_answers_, answered_ = 0, 0

    for index_, question_ in enumerate(questions_):
        __print_question(index_, len(questions_), question_)

        valid_answers_ = [__letter(idx_) for idx_ in range(0, len(question_.choices))]
        answer_string_ = ""
        while answer_string_ not in valid_answers_ and answer_string_ != QUIT:
            answer_string_ = input(f"Answer ({'/'.join(valid_answers_)} or {QUIT}): ").strip().upper()
            answer_string_ = QUIT if answer_string_.lower() == QUIT else answer_string_
        print()

        if answer_string_ == QUIT:
            break

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
    print()

    return float(correct_answers_) / answered_ if answered_ > 0 else -1.0
