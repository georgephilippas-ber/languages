from os import environ
from os.path import dirname, sep
from dotenv import load_dotenv
from json import loads
from openai import OpenAI

from src.domain import Vocabulary, Entry, SingleMultipleChoiceQuestion, CEFRLevel
from src.openai_prompt import single_multiple_choice_question_prompt

client_ = OpenAI()


def get_openai_secret_key() -> str:
    load_dotenv(sep.join([str(dirname(__file__)), "..", ".env"]))
    return environ["OPENAI_API_KEY"]


def openai_construct_single_multiple_choice_question(entry_: Entry,
                                                     vocabulary_: Vocabulary,
                                                     cefr_level_: CEFRLevel = CEFRLevel.C1) -> SingleMultipleChoiceQuestion:
    prompt_: str = single_multiple_choice_question_prompt(entry_, vocabulary_, cefr_level_)

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


if __name__ == "__main__":
    pass
