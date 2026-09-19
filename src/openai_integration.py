from json import loads
from os.path import dirname, sep
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from .domain import Vocabulary, Entry, SingleMultipleChoiceQuestion, CEFRLevel
from .openai_prompt import single_multiple_choice_question_prompt


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
    )


