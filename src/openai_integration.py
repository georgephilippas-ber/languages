from json import loads, JSONDecodeError
from os.path import dirname, sep
from random import sample
from time import perf_counter
from typing import List, Tuple, Dict, Any, Optional

from dotenv import load_dotenv
from faker import Faker
from openai import OpenAI

from src.database import retrieve_used_terms, insert_term
from src.research import sample_weighted

from .domain import Vocabulary, Entry, SingleMultipleChoiceQuestion, CEFRLevel
from .openai_prompt import multiple_choice_questions_prompt
from .parser import parse_vocabulary_to_dict, parse_vocabulary_to_list


def get_openai_client() -> OpenAI:
    load_dotenv(sep.join([str(dirname(__file__)), "..", ".env"]))
    return OpenAI()


client_ = get_openai_client()


QUESTION_KEYS: List[str] = ["question", "choices", "correct_choice", "complete_sentence", "english_translation"]


def __strip_code_fences(text_: str) -> str:
    # Some models wrap JSON in ```json ... ``` despite being asked not to.
    text_ = text_.strip()
    if text_.startswith("```"):
        text_ = text_.split("\n", 1)[1] if "\n" in text_ else ""
        text_ = text_.rsplit("```", 1)[0]

    return text_.strip()


def __question_from_json(question_json_: Dict[str, Any]) -> SingleMultipleChoiceQuestion:
    """Raises ValueError when a question is unusable, e.g. a missing field or an out-of-range correct_choice."""
    missing_ = [key_ for key_ in QUESTION_KEYS if key_ not in question_json_]
    if missing_:
        raise ValueError(f"missing {', '.join(missing_)}")

    choices_ = question_json_["choices"]
    correct_choice_ = question_json_["correct_choice"]
    if not isinstance(choices_, list) or len(choices_) < 2:
        raise ValueError("fewer than two choices")
    if not isinstance(correct_choice_, int) or not 0 <= correct_choice_ < len(choices_):
        raise ValueError(f"correct_choice {correct_choice_!r} does not point to a choice")

    return SingleMultipleChoiceQuestion(
        question=question_json_["question"],
        choices=choices_,
        correct_choice=correct_choice_,
        complete_sentence=question_json_["complete_sentence"],
        english_translation=question_json_["english_translation"],
        choices_translations=question_json_.get("choices_translations", [])
    )


def parse_multiple_choice_questions_response(response_text_: str, entries_: List[Entry]) -> \
        List[Tuple[Entry, SingleMultipleChoiceQuestion]]:
    """Matches the questions in the response to entries_ by their id (1-based position in entries_). Unusable or
    missing questions are reported and skipped, so that one bad question does not cost the whole exercise."""
    response_json_ = loads(__strip_code_fences(response_text_))
    questions_json_ = response_json_["questions"] if isinstance(response_json_, dict) else response_json_

    questions_by_id_: Dict[int, SingleMultipleChoiceQuestion] = {}
    returned_ids_ = set()
    for position_, question_json_ in enumerate(questions_json_, start=1):
        id_ = question_json_.get("id", position_) if isinstance(question_json_, dict) else position_
        if not isinstance(id_, int) or not 1 <= id_ <= len(entries_) or id_ in questions_by_id_:
            print(f"Skipped a question with an unexpected id ({id_!r}).")
            continue
        returned_ids_.add(id_)
        try:
            questions_by_id_[id_] = __question_from_json(question_json_)
        except (ValueError, TypeError, AttributeError) as error_:
            print(f"Skipped the question for '{entries_[id_ - 1].term}': {error_}.")

    for id_, entry_ in enumerate(entries_, start=1):
        if id_ not in returned_ids_:
            print(f"No question was returned for '{entry_.term}'.")

    return [(entries_[id_ - 1], questions_by_id_[id_]) for id_ in sorted(questions_by_id_)]


def openai_construct_multiple_choice_questions(entries_alternatives_: List[Tuple[Entry, List[str]]],
                                               vocabulary_: Vocabulary = Vocabulary.GERMAN,
                                               cefr_level_: CEFRLevel = CEFRLevel.C1, *,
                                               demo: bool = False) -> List[SingleMultipleChoiceQuestion]:
    """Creates all questions of an exercise with a single request instead of one request per question."""
    if demo:
        faker_ = Faker()

        return [SingleMultipleChoiceQuestion(
            question=faker_.sentence(),
            choices=[faker_.word() for _ in range(4)],
            correct_choice=0,
            complete_sentence=faker_.sentence(),
            english_translation=faker_.sentence(),
            choices_translations=[faker_.word() for _ in range(4)]
        ) for _ in entries_alternatives_]

    prompt_: str = multiple_choice_questions_prompt(entries_alternatives_, vocabulary_, cefr_level_)

    openai_response_ = client_.responses.create(
        model="gpt-6-sol",
        input=prompt_,
    )

    entries_questions_ = parse_multiple_choice_questions_response(
        openai_response_.output_text, [entry_ for entry_, _ in entries_alternatives_])

    # Only terms that actually got a question count as trained.
    for entry_, _ in entries_questions_:
        insert_term(entry_.term, vocabulary_)

    return [question_ for _, question_ in entries_questions_]


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


def sample_alternatives_(term_: str, terms_population_: List[str], vocabulary_: Vocabulary,
                         file_numbers_: Optional[List[int]], alternatives_number_: int,
                         earlier_files_terms_: Dict[int, List[str]]) -> List[str]:
    """Wrong answer choices for term_, taken from the quiz's own files. When they are too small, the missing ones
    come from the file before the first of them, then the one before that, and so on. earlier_files_terms_ caches
    the terms of those earlier files between questions."""
    candidates_ = [candidate_ for candidate_ in terms_population_ if candidate_ != term_]
    alternatives_ = sample(candidates_, min(alternatives_number_, len(candidates_)))

    earlier_file_number_ = (min(file_numbers_) - 1) if file_numbers_ else 0
    while len(alternatives_) < alternatives_number_ and earlier_file_number_ >= 1:
        if earlier_file_number_ not in earlier_files_terms_:
            earlier_files_terms_[earlier_file_number_] = [
                entry_.term for entry_ in parse_vocabulary_to_list(vocabulary_, [earlier_file_number_])]

        earlier_candidates_ = [candidate_ for candidate_ in earlier_files_terms_[earlier_file_number_]
                               if candidate_ != term_ and candidate_ not in alternatives_]
        alternatives_ += sample(earlier_candidates_,
                                min(alternatives_number_ - len(alternatives_), len(earlier_candidates_)))
        earlier_file_number_ -= 1

    return alternatives_


def openai_construct_exercise(questions_number: int = 10, *, vocabulary_: Vocabulary = Vocabulary.GERMAN,
                              cefr_level_: CEFRLevel = CEFRLevel.C1,
                              alternatives_per_questions_: int = 3, demo: bool = False, unseen_alpha=30,
                              file_numbers_: Optional[List[int]] = None) -> List[SingleMultipleChoiceQuestion]:
    """file_numbers_ selects the files the questions come from; None uses all of the language's files."""
    entries_population_: Dict[str, Tuple[Entry, int]] = parse_vocabulary_to_dict(vocabulary_, file_numbers_)
    seen_: List[str] = retrieve_used_terms(vocabulary_)

    questions_entries_sample_: List[Entry] = sample_(entries_population_, seen_, questions_number, unseen_alpha)

    terms_population_ = [word_ for word_ in entries_population_]
    earlier_files_terms_: Dict[int, List[str]] = {}

    entries_alternatives_: List[Tuple[Entry, List[str]]] = [
        (entry_, sample_alternatives_(entry_.term, terms_population_, vocabulary_, file_numbers_,
                                      alternatives_per_questions_, earlier_files_terms_))
        for entry_ in questions_entries_sample_]

    print(f"Generating {len(entries_alternatives_)} question{'s' if len(entries_alternatives_) != 1 else ''}...")
    started_at_ = perf_counter()
    try:
        return_ = openai_construct_multiple_choice_questions(entries_alternatives_, vocabulary_, cefr_level_,
                                                             demo=demo)
    except (JSONDecodeError, KeyError, TypeError) as error_:
        print(f"The response could not be read as questions ({type(error_).__name__}: {error_}).")
        return_ = []
    else:
        print(f"Ready ({perf_counter() - started_at_:.1f} s).")
    print()

    return return_
