import argparse

from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_CEFR_LEVEL, DEFAULT_VOCABULARY, UNSEEN_ALPHA


def positive_integer(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or int(value) <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return int(value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a German vocabulary exercise.")
    parser.add_argument("questions_number", nargs="?", default=DEFAULT_NUMBER_OF_QUESTIONS, type=positive_integer,
                        help="number of questions (positive integer; default: 10)")
    args = parser.parse_args()

    from src.launcher import launch_console
    from src.openai_integration import openai_construct_exercise

    print(launch_console(
        openai_construct_exercise(questions_number=args.questions_number, vocabulary_=DEFAULT_VOCABULARY,
                                  cefr_level_=DEFAULT_CEFR_LEVEL, unseen_alpha=UNSEEN_ALPHA)) * 100)
