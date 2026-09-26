from typing import List

from src.domain import SingleMultipleChoiceQuestion


def launch_console(questions_: List[SingleMultipleChoiceQuestion]) -> float:
    correct_answers_ = 0

    for index_, question_ in enumerate(questions_):
        print(f"Question {index_ + 1}:")
        print()
        print(question_.question)
        print()

        for choice_index_, choice_ in enumerate(question_.choices):
            print(f"{chr(ord('A') + choice_index_)}. {choice_}")

        answer_string_ = ""
        while answer_string_ not in [chr(ord('A') + idx_) for idx_ in range(0, len(question_.choices))]:
            answer_string_ = input("Answer: ").strip().upper()

        if ord(answer_string_) - 65 == question_.correct_choice:
            correct_answers_ += 1
            print("Correct.")
        else:
            print(f"Incorrect. ({chr(ord('A') + question_.correct_choice)})")
        print(" ".join(["sentence:", question_.complete_sentence]))
        print(" ".join(["translation:", question_.english_translation]))
        print()

    return float(correct_answers_) / len(questions_) if len(questions_) > 0 else -1.0
