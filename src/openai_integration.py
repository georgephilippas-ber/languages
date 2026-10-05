from json import loads
from os.path import dirname, sep
from random import sample
from typing import List, Tuple, Dict, Any, Optional

from dotenv import load_dotenv
from faker import Faker
from openai import OpenAI

from src.database import retrieve_used_terms, insert_term
from src.research import sample_weighted

from .domain import Vocabulary, Entry, SingleMultipleChoiceQuestion, CEFRLevel, WritingQuestionEvaluation
from .openai_prompt import single_multiple_choice_question_prompt, writing_question_prompt, \
    correct_writing_question_prompt
from .parser import parse_vocabulary_to_dict, parse_vocabulary_to_list


def get_openai_client() -> OpenAI:
    load_dotenv(sep.join([str(dirname(__file__)), "..", ".env"]))
    return OpenAI()


client_ = get_openai_client()


def openai_construct_single_multiple_choice_question(entry_: Entry, alternatives_: List[str],
                                                     vocabulary_: Vocabulary = Vocabulary.GERMAN,
                                                     cefr_level_: CEFRLevel = CEFRLevel.C1, *,
                                                     demo: bool = False) -> SingleMultipleChoiceQuestion:
    prompt_: str = single_multiple_choice_question_prompt(entry_, alternatives_, vocabulary_, cefr_level_)

    if not demo:
        insert_term(entry_.term, vocabulary_)
        openai_response_ = client_.responses.create(
            model="gpt-6-sol",
            input=prompt_,
        )

        response_json_ = loads(openai_response_.output_text)

        return SingleMultipleChoiceQuestion(
            question=response_json_["question"],
            choices=response_json_["choices"],
            correct_choice=response_json_["correct_choice"],
            complete_sentence=response_json_["complete_sentence"],
            english_translation=response_json_["english_translation"],
            choices_translations=response_json_.get("choices_translations", [])
        )
    else:
        faker_ = Faker()

        return SingleMultipleChoiceQuestion(
            question=faker_.sentence(),
            choices=[faker_.word() for _ in range(4)],
            correct_choice=0,
            complete_sentence=faker_.sentence(),
            english_translation=faker_.sentence(),
            choices_translations=[faker_.word() for _ in range(4)]
        )


def sample_(entries_population_: Dict[str, Tuple[Entry, int]], seen_: List[str], questions_number: int,
            unseen_alpha: int = 5) -> List[Entry]:
    n_: int = len(seen_)

    for i_, term_ in enumerate(seen_):
        if term_ in entries_population_:
            entries_population_[term_] = (entries_population_[term_][0], i_)

    for term_ in entries_population_:
        if term_ not in seen_:
            entries_population_[term_] = (entries_population_[term_][0], (n_ + 1) + unseen_alpha)

    population_list_: List[Tuple[Entry, int]] = list(entries_population_.values())

    return sample_weighted([element_[0] for element_ in population_list_], questions_number,
                           [element_[1] for element_ in population_list_])


def openai_construct_exercise(questions_number: int = 10, *, vocabulary_: Vocabulary = Vocabulary.GERMAN,
                              cefr_level_: CEFRLevel = CEFRLevel.C1,
                              alternatives_per_questions_: int = 3, demo: bool = False, unseen_alpha=30,
                              file_number_: Optional[int] = None) -> List[SingleMultipleChoiceQuestion]:
    entries_population_: Dict[str, Tuple[Entry, int]] = parse_vocabulary_to_dict(vocabulary_, file_number_)
    seen_: List[str] = retrieve_used_terms(vocabulary_)

    questions_entries_sample_: List[Entry] = sample_(entries_population_, seen_, questions_number, unseen_alpha)

    terms_population_ = [word_ for word_ in entries_population_]

    print("Generating...")
    return_: List[SingleMultipleChoiceQuestion] = []
    for i_, entry_ in enumerate(questions_entries_sample_):
        alternatives_sample_ = sample([term_ for term_ in terms_population_ if term_ != entry_.term],
                                      alternatives_per_questions_)

        return_.append(openai_construct_single_multiple_choice_question(entry_, alternatives_sample_,
                                                                        vocabulary_, cefr_level_, demo=demo))
        print("{:.2f}%".format(float(i_ + 1) / questions_number * 100.))
    print()
    print("Ready.")

    return return_


def single_writing_exercise(vocabulary_entries_: List[Entry], vocabulary: Vocabulary, cefr_level: CEFRLevel):
    prompt_ = writing_question_prompt(vocabulary_entries_, cefr_level)

    openai_response_ = client_.responses.create(
        model="gpt-6-sol",
        input=prompt_,
    )

    response_json_ = loads(openai_response_.output_text)

    print("Write a short text on the following subject:")
    print()
    print(response_json_['question'])
    print()
    answer_ = input("Answer:\n\n")

    if answer_.strip().lower() == 'quit' or answer_.strip() == '':
        return

    prompt_2 = correct_writing_question_prompt(vocabulary, cefr_level, response_json_['question'], answer_)

    openai_response_2 = client_.responses.create(
        model="gpt-6-sol",
        input=prompt_2,
    )

    evaluation_: WritingQuestionEvaluation = WritingQuestionEvaluation(**loads(openai_response_2.output_text))
    print()
    print("Score: ", evaluation_.score)
    print()
    print("Grammar")
    print("\t" + evaluation_.grammar_comments)
    print("Syntax")
    print("\t" + evaluation_.syntax_comments)
    print("Spelling")
    print("\t" + evaluation_.spelling_comments)
    print()
    print(' '.join([evaluation_.general_comments, evaluation_.encouraging_objective_remark]))
    print()
    print("Closest correct answer:")
    print("\t" + evaluation_.correct_answer_student)
    print("Correct answer for that level:")
    print("\t" + evaluation_.correct_answer_level)

    if __name__ == "__main__":
        pass
