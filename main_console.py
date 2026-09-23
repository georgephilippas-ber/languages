import argparse


def positive_integer(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or int(value) <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return int(value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a German vocabulary exercise.")
    parser.add_argument("questions_number", nargs="?", default=10, type=positive_integer,
                        help="number of questions (positive integer; default: 10)")
    args = parser.parse_args()

    from src.domain import Vocabulary, CEFRLevel
    from src.launcher import launch_console
    from src.openai_integration import openai_construct_exercise

    print(launch_console(openai_construct_exercise(questions_number=args.questions_number, vocabulary_=Vocabulary.GERMAN, cefr_level_=CEFRLevel.C1)) * 100)
