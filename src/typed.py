from dataclasses import dataclass
from json import dumps, loads, JSONDecodeError
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from src.configuration import MODEL, UNSEEN_ALPHA
from src.database import retrieve_used_terms, insert_term
from src.domain import Vocabulary, Entry, CEFRLevel, BLANK, Correction
from src.openai_integration import get_openai_client, strip_code_fences, sample_, sample_alternatives_
from src.parser import parse_vocabulary_to_dict

ALTERNATIVES_PER_QUESTION: int = 3

CHOICES_LANGUAGE: Dict[Vocabulary, str] = {Vocabulary.GERMAN: "English", Vocabulary.FRENCH: "English",
                                           Vocabulary.ENGLISH: "French"}

QUESTION_KEYS: List[str] = ["question", "choices", "choices_translations", "correct_choice", "correct_answer",
                            "complete_sentence", "english_translation"]
VERDICTS: List[str] = ["correct", "wrong_form", "wrong_word"]


@dataclass
class TypedQuestion:
    term: str
    question: str
    choices: List[str]
    choices_translations: List[str]
    correct_choice: int
    correct_answer: str
    complete_sentence: str
    english_translation: str


@dataclass
class TypedCorrection:
    verdict: str
    corrected_answer: str
    errors: List[Correction]
    comment: str
    suggestions: List[str]


def questions_prompt(entries_alternatives_: List[Tuple[Entry, List[str]]], vocabulary_: Vocabulary,
                     cefr_level_: CEFRLevel) -> str:
    language_ = vocabulary_.name.lower()
    choices_language_ = CHOICES_LANGUAGE[vocabulary_]
    items_ = [{"id": id_,
               "target_entry": {key_: value_ for key_, value_ in vars(entry_).items()
                                if key_ != "example" and value_ is not None},
               "incorrect_choice_terms": alternatives_}
              for id_, (entry_, alternatives_) in enumerate(entries_alternatives_, start=1)]

    return f"""
Create exactly {len(items_)} {language_} fill-in-the-blank vocabulary questions at CEFR level {cefr_level_.name}, one
for each item below. The learner will NOT see the {language_} choices: they will see only the {choices_language_}
meaning of each choice, and must TYPE the missing {language_} word(s) themselves, in exactly the form the sentence
requires (case, gender, number, conjugation, agreement, spelling).

Items JSON (one question per item; "incorrect_choice_terms" are the vocabulary terms that MUST be used as that
question's incorrect choices):

{dumps(items_, ensure_ascii=False, indent=1)}

Requirements for every question:
- Write [question] entirely in {language_}, with exactly one blank written as {BLANK}.
- The blank must be one contiguous span that the learner can type. If the term's form is split in the sentence
  (e.g. a separable verb prefix, a reflexive pronoun, the second part of a two-part preposition), keep the separated
  part in the sentence and blank only the contiguous part that tests the term.
- The sentence must be natural, idiomatic, appropriate for CEFR level {cefr_level_.name}, and at least 10 words long.
  Humour is allowed and encouraged. Use a different context or subject for each question; preferred subjects:
  everyday life, law, economics, finance.
- The sentence must make the required form unambiguous (e.g. the case is determined by a preposition or verb, the
  gender and number by an article or agreement), so that exactly one form is correct.
- The intended correct answer must be the item's target vocabulary term.
- [choices] must contain the item's incorrect_choice_terms, changed only to match the blank's part of speech and
  form, plus the correct answer. Invent extra distractors ONLY if incorrect_choice_terms has fewer than three terms.
- Exactly one choice must be semantically and contextually correct; the distinction must be subtle enough to be
  useful at CEFR level {cefr_level_.name}, but only one answer may be defensible.
- Randomize the position of the correct answer among the four choices, independently for each question.
- [choices_translations] must have exactly one entry per choice, in the same order as [choices]: the short
  {choices_language_} meaning of that choice as it would read in the blank (e.g. "to advance", "tiny"). It must NOT
  reveal the {language_} word, and must not contain numbering, letters, or commentary.
- [correct_choice] must be the zero-based index of the correct choice.
- [correct_answer] must be exactly the {language_} text that fills the blank, in the required form, so that replacing
  {BLANK} in [question] with it gives [complete_sentence].
- [complete_sentence] is [question] with the blank filled by [correct_answer].
- [english_translation] must contain ONLY the English translation of [complete_sentence].
- [id] must be the id of the item the question was created for.
- Do not reveal the answer anywhere except in [choices], [correct_answer], and [complete_sentence].

Return only the requested JSON object, with exactly one question per item in the order of the items, and no
explanation, commentary, or Markdown code fences.

Output shape:
{{
    "questions": [
        {{
            "id": int,
            "question": str,
            "choices": List[str],
            "choices_translations": List[str],
            "correct_choice": int,
            "correct_answer": str,
            "complete_sentence": str,
            "english_translation": str
        }}
    ]
}}"""


def __question_from_json(term_: str, question_json_: Dict[str, Any]) -> TypedQuestion:
    missing_ = [key_ for key_ in QUESTION_KEYS if key_ not in question_json_]
    if missing_:
        raise ValueError(f"missing {', '.join(missing_)}")

    question_ = str(question_json_["question"])
    choices_, translations_ = question_json_["choices"], question_json_["choices_translations"]
    correct_choice_ = question_json_["correct_choice"]
    correct_answer_ = str(question_json_["correct_answer"]).strip()
    if question_.count(BLANK) != 1:
        raise ValueError(f"the question does not contain exactly one blank {BLANK}")
    if not isinstance(choices_, list) or len(choices_) < 2:
        raise ValueError("fewer than two choices")
    if not isinstance(translations_, list) or len(translations_) != len(choices_):
        raise ValueError("not one translation per choice")
    if not isinstance(correct_choice_, int) or not 0 <= correct_choice_ < len(choices_):
        raise ValueError(f"correct_choice {correct_choice_!r} does not point to a choice")
    if not correct_answer_:
        raise ValueError("empty correct_answer")

    return TypedQuestion(term=term_, question=question_, choices=[str(choice_) for choice_ in choices_],
                         choices_translations=[str(translation_) for translation_ in translations_],
                         correct_choice=correct_choice_, correct_answer=correct_answer_,
                         complete_sentence=str(question_json_["complete_sentence"]),
                         english_translation=str(question_json_["english_translation"]))


def parse_questions_response(response_text_: str, entries_: List[Entry]) -> List[TypedQuestion]:
    response_json_ = loads(strip_code_fences(response_text_))
    questions_json_ = response_json_["questions"] if isinstance(response_json_, dict) else response_json_

    questions_by_id_: Dict[int, TypedQuestion] = {}
    for position_, question_json_ in enumerate(questions_json_, start=1):
        id_ = question_json_.get("id", position_) if isinstance(question_json_, dict) else position_
        if not isinstance(id_, int) or not 1 <= id_ <= len(entries_) or id_ in questions_by_id_:
            print(f"Skipped a question with an unexpected id ({id_!r}).")
            continue
        try:
            questions_by_id_[id_] = __question_from_json(entries_[id_ - 1].term, question_json_)
        except (ValueError, TypeError, AttributeError) as error_:
            print(f"Skipped the question for '{entries_[id_ - 1].term}': {error_}.")

    for id_, entry_ in enumerate(entries_, start=1):
        if id_ not in questions_by_id_:
            print(f"No usable question was returned for '{entry_.term}'.")

    return [questions_by_id_[id_] for id_ in sorted(questions_by_id_)]


def __demo_questions(entries_alternatives_: List[Tuple[Entry, List[str]]]) -> List[TypedQuestion]:
    return [TypedQuestion(term=entry_.term, question=f"Demo: type the word for '{entry_.term}' here: {BLANK}.",
                          choices=[entry_.term] + alternatives_,
                          choices_translations=[(entry_.english or entry_.term)[:40]] +
                                               [f"(meaning of {alternative_})" for alternative_ in alternatives_],
                          correct_choice=0, correct_answer=entry_.term,
                          complete_sentence=f"Demo: type the word for '{entry_.term}' here: {entry_.term}.",
                          english_translation="(demo)")
            for entry_, alternatives_ in entries_alternatives_]


def construct_questions(vocabulary_: Vocabulary, cefr_level_: CEFRLevel, questions_number_: int,
                        file_numbers_: List[int], demo_: bool = False) -> List[TypedQuestion]:
    entries_population_ = parse_vocabulary_to_dict(vocabulary_, file_numbers_)
    entries_ = sample_(entries_population_, retrieve_used_terms(vocabulary_), questions_number_, UNSEEN_ALPHA)
    terms_population_ = list(entries_population_)
    earlier_files_terms_: Dict[int, List[str]] = {}
    entries_alternatives_ = [(entry_, sample_alternatives_(entry_.term, terms_population_, vocabulary_, file_numbers_,
                                                           ALTERNATIVES_PER_QUESTION, earlier_files_terms_))
                             for entry_ in entries_]

    if demo_:
        return __demo_questions(entries_alternatives_)

    print(f"Generating {len(entries_)} question{'s' if len(entries_) != 1 else ''}...")
    started_at_ = perf_counter()
    try:
        response_ = get_openai_client().responses.create(
            model=MODEL, input=questions_prompt(entries_alternatives_, vocabulary_, cefr_level_))
        questions_ = parse_questions_response(response_.output_text, entries_)
    except (JSONDecodeError, KeyError, TypeError) as error_:
        print(f"The response could not be read as questions ({type(error_).__name__}: {error_}).")
        return []
    print(f"Ready ({perf_counter() - started_at_:.1f} s).")
    print()

    for question_ in questions_:
        insert_term(question_.term, vocabulary_)

    return questions_


def correction_prompt(vocabulary_: Vocabulary, question_: TypedQuestion, answer_: str) -> str:
    language_ = vocabulary_.name.capitalize()
    choices_ = "\n".join(f'- "{choice_}" ({translation_})'
                         for choice_, translation_ in zip(question_.choices, question_.choices_translations))

    return f"""
You are an experienced {language_} teacher. A learner was given this {language_} sentence with one blank:

\"\"\"{question_.question}\"\"\"

They saw only the {CHOICES_LANGUAGE[vocabulary_]} meanings of these choices, and had to type the missing {language_}
word(s) themselves, in the form the sentence requires:
{choices_}

The vocabulary term being tested: "{question_.term}"
The expected answer: "{question_.correct_answer}"
The complete sentence: "{question_.complete_sentence}"

The learner typed:
\"\"\"{answer_}\"\"\"

Tasks:
- Decide the verdict:
  "correct": the learner's text fits the blank exactly, in meaning and form, including spelling, umlauts, and
  capitalisation. A different word is also correct if it fits the sentence equally well and correctly.
  "wrong_form": the right word (or an equally good one), but with an error of form: case, gender, number, ending,
  conjugation, tense, word order, spelling, or capitalisation.
  "wrong_word": a word that does not fit the meaning or the context, or no recognisable attempt.
- In "corrected_answer", give the learner's own word in the correct form if the verdict is "wrong_form", the expected
  answer if it is "wrong_word", and the learner's text unchanged if it is "correct".
- List every error in "errors", each with the learner's original, the correction, and a short explanation in English
  of the rule involved (e.g. which case the preposition or verb requires, and why).
- In "comment", explain briefly in English why the expected answer is right here, and if the learner chose another
  choice, how its meaning differs.
- In "suggestions", give one to three short, practical tips in English: related forms, a useful pattern or
  collocation, or a way to remember the distinction. Mention other answers that would also fit, if any.

Return only a JSON object, with no Markdown code fences and no other text:
{{
    "verdict": "correct" | "wrong_form" | "wrong_word",
    "corrected_answer": str,
    "errors": [
        {{"original": str, "corrected": str, "explanation": str}}
    ],
    "comment": str,
    "suggestions": [str]
}}"""


def correct_answer(vocabulary_: Vocabulary, question_: TypedQuestion, answer_: str,
                   demo_: bool = False) -> Dict[str, Any]:
    if demo_:
        verdict_ = "correct" if answer_ == question_.correct_answer else \
            "wrong_form" if answer_.lower() == question_.correct_answer.lower() else "wrong_word"
        return {"verdict": verdict_, "corrected_answer": question_.correct_answer, "errors": [],
                "comment": "(demo: compared with the expected answer, without calling the API)", "suggestions": []}

    response_ = get_openai_client().responses.create(model=MODEL,
                                                     input=correction_prompt(vocabulary_, question_, answer_))
    correction_ = loads(strip_code_fences(response_.output_text))
    if not isinstance(correction_, dict):
        raise TypeError("the response is not a JSON object")

    return correction_


def normalize_correction(question_: TypedQuestion, correction_: Dict[str, Any]) -> TypedCorrection:
    verdict_ = str(correction_.get("verdict", "")).strip()
    errors_ = correction_.get("errors", [])
    errors_ = [item_ for item_ in errors_ if isinstance(item_, dict)] if isinstance(errors_, list) else []
    suggestions_ = correction_.get("suggestions", [])

    return TypedCorrection(
        verdict=verdict_ if verdict_ in VERDICTS else "wrong_word",
        corrected_answer=str(correction_.get("corrected_answer") or question_.correct_answer),
        errors=[Correction(original=str(item_.get("original", "")), corrected=str(item_.get("corrected", "")),
                           explanation=str(item_.get("explanation") or "")) for item_ in errors_],
        comment=str(correction_.get("comment") or ""),
        suggestions=[str(item_) for item_ in suggestions_ if item_] if isinstance(suggestions_, list) else [])


def check_answer(vocabulary_: Vocabulary, question_: TypedQuestion, answer_: str,
                 demo_: bool = False) -> Tuple[TypedCorrection, Optional[str]]:
    try:
        return normalize_correction(question_, correct_answer(vocabulary_, question_, answer_, demo_)), None
    except (JSONDecodeError, KeyError, TypeError) as error_:
        fallback_ = {"verdict": "correct" if answer_ == question_.correct_answer else "wrong_word"}
        return normalize_correction(question_, fallback_), \
            f"The correction could not be read ({type(error_).__name__}: {error_})."
