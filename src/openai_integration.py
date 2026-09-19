from json import loads
from os.path import dirname, sep
from random import sample, seed
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from .domain import Vocabulary, Entry, SingleMultipleChoiceQuestion, CEFRLevel
from .openai_prompt import single_multiple_choice_question_prompt
from .parser import parse_vocabulary


def get_openai_client() -> OpenAI:
    load_dotenv(sep.join([str(dirname(__file__)), "..", ".env"]))
    return OpenAI()

client_ = get_openai_client()

def openai_construct_single_multiple_choice_question(entry_: Entry, alternatives_: List[str],
                                                     vocabulary_: Vocabulary,
                                                     cefr_level_: CEFRLevel = CEFRLevel.C1) -> SingleMultipleChoiceQuestion:
    prompt_: str = single_multiple_choice_question_prompt(entry_, alternatives_, vocabulary_, cefr_level_)

    openai_response_ = client_.responses.create(
        model="gpt-5.6-luna",
        input=prompt_,
    )

    response_json_ = loads(openai_response_.output_text)

    return SingleMultipleChoiceQuestion(
        question=response_json_["question"],
        choices=response_json_["choices"],
        correct_choice=response_json_["correct_choice"],
        english_translation=response_json_["english_translation"]
    )

def openai_construct_exercise(questions_: int = 10, *, vocabulary_: Vocabulary = Vocabulary.GERMAN, cefr_level_: CEFRLevel = CEFRLevel.C1,
                  alternatives_per_questions_: int = 3) -> List[SingleMultipleChoiceQuestion]:
    entries_population_: List[Entry] = parse_vocabulary(vocabulary_)

    terms_population_ = [word_.term for word_ in entries_population_]

    entries_sample_ = sample(entries_population_, questions_)

    print("Generating...")
    return_: List[SingleMultipleChoiceQuestion] = []
    for i_, entry_ in enumerate(entries_sample_):
        return_.append(openai_construct_single_multiple_choice_question(entry_, sample(terms_population_,
                                                                                       alternatives_per_questions_),
                                                                        vocabulary_, cefr_level_))
        print("{:.2f}%".format(float(i_ + 1) / questions_ * 100.))
    print()
    print("Ready.")

    return return_
