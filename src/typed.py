from dataclasses import dataclass
from json import dumps, loads, JSONDecodeError
import re
from unicodedata import combining, normalize
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from src.configuration import UNSEEN_ALPHA
from src.database import retrieve_used_terms, insert_term
from src.domain import Vocabulary, Entry, CEFRLevel, BLANK, Correction
from src.openai_integration import get_openai_client, current_model, strip_code_fences, sample_
from src.parser import parse_vocabulary_to_dict

CHOICES_LANGUAGE: Dict[Vocabulary, str] = {Vocabulary.GERMAN: "English", Vocabulary.FRENCH: "English",
                                           Vocabulary.ENGLISH: "French"}

QUESTION_KEYS: List[str] = ["question", "correct_answer", "complete_sentence", "english_translation"]
VERDICTS: List[str] = ["correct", "wrong_form", "wrong_word"]


@dataclass
class TypedQuestion:
    term: str
    question: str
    hint: str
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


def hint(entry_: Entry) -> str:
    return (entry_.english or "").split("·")[0].strip() or entry_.definition or ""


def safe_hint(entry_: Entry, answer_: str) -> str:
    def normalized(value_: str) -> str:
        decomposed_ = normalize("NFKD", value_).casefold().replace("’", "'").replace("‘", "'")
        return " ".join("".join(char_ for char_ in decomposed_ if not combining(char_)).split())
    term_ = normalized(entry_.term)
    bare_term_ = re.sub(r"^(?:(?:to|der|die|das|le|la|les)\s+|l')", "", term_)
    candidates_ = (normalized(answer_), term_, bare_term_)
    for source_ in (hint(entry_), entry_.definition or ""):
        text_ = normalized(source_)
        if text_ and not any(candidate_ and candidate_ in text_ for candidate_ in candidates_):
            return source_
    return ""


def questions_prompt(entries_: List[Entry], vocabulary_: Vocabulary, cefr_level_: CEFRLevel) -> str:
    language_ = vocabulary_.name.lower()
    items_ = [{"id": id_,
               "target_entry": {key_: value_ for key_, value_ in vars(entry_).items()
                                if key_ != "example" and value_ is not None}}
              for id_, entry_ in enumerate(entries_, start=1)]

    return f"""
Create one concise, natural {language_} fill-in-the-blank question per item at CEFR level {cefr_level_.name}.
Return the questions in item order with their original ids.

- Write a short, unambiguous sentence with exactly one {BLANK}; its answer is the target term in the form required by
  the sentence. Blank one contiguous span; leave any separated verb prefix or other separated part in the sentence.
- [question] contains only the exercise sentence. Do not add hints, glosses, translations, definitions, or labelled
  notes or disclose the answer elsewhere. The app supplies any meaning hint separately.
- Set [correct_answer] to the exact missing text and [complete_sentence] to [question] with {BLANK} replaced by it.
  Set [english_translation] to the English translation of [complete_sentence].
- Vary the context across everyday life, law, economics, and finance. Humour is welcome.

Items: {dumps(items_, ensure_ascii=False, separators=(",", ":"))}

Return only JSON: {{"questions":[{{"id":int,"question":str,"correct_answer":str,
"complete_sentence":str,"english_translation":str}}]}}
"""


def strip_question_hint(text_: str) -> str:
    labels_ = r"(?:hint|clue|hinweis|indice)"
    text_ = re.sub(rf"\s*\(\s*{labels_}\s*:\s*(?:[^()]|\([^()]*\))*\)", "", text_, flags=re.I)
    text_ = re.sub(rf"\s*\[\s*{labels_}\s*:\s*[^\[\]]*\]", "", text_, flags=re.I)
    text_ = re.sub(rf"([.!?])\s*(?:[—–-]\s*)?{labels_}\s*:.*$", r"\1", text_, flags=re.I | re.S)
    text_ = re.sub(rf"\n\s*{labels_}\s*:.*$", "", text_, flags=re.I | re.S)
    return text_.strip()


def __question_from_json(entry_: Entry, question_json_: Dict[str, Any]) -> TypedQuestion:
    missing_ = [key_ for key_ in QUESTION_KEYS if key_ not in question_json_]
    if missing_:
        raise ValueError(f"missing {', '.join(missing_)}")

    question_ = strip_question_hint(str(question_json_["question"]))
    correct_answer_ = str(question_json_["correct_answer"]).strip()
    if question_.count(BLANK) != 1:
        raise ValueError(f"the question does not contain exactly one blank {BLANK}")
    if not correct_answer_:
        raise ValueError("empty correct_answer")

    return TypedQuestion(term=entry_.term, question=question_, hint=safe_hint(entry_, correct_answer_), correct_answer=correct_answer_,
                         complete_sentence=question_.replace(BLANK, correct_answer_),
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
            questions_by_id_[id_] = __question_from_json(entries_[id_ - 1], question_json_)
        except (ValueError, TypeError, AttributeError) as error_:
            print(f"Skipped the question for '{entries_[id_ - 1].term}': {error_}.")

    for id_, entry_ in enumerate(entries_, start=1):
        if id_ not in questions_by_id_:
            print(f"No usable question was returned for '{entry_.term}'.")

    return [questions_by_id_[id_] for id_ in sorted(questions_by_id_)]


def construct_questions(vocabulary_: Vocabulary, cefr_level_: CEFRLevel, questions_number_: int,
                        file_numbers_: List[int]) -> List[TypedQuestion]:
    entries_population_ = parse_vocabulary_to_dict(vocabulary_, file_numbers_)
    entries_ = sample_(entries_population_, retrieve_used_terms(vocabulary_), questions_number_, UNSEEN_ALPHA)

    print(f"Generating {len(entries_)} question{'s' if len(entries_) != 1 else ''}...")
    started_at_ = perf_counter()
    try:
        response_ = get_openai_client().responses.create(
            model=current_model(), input=questions_prompt(entries_, vocabulary_, cefr_level_))
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

    return f"""
You are an experienced {language_} teacher. A learner was given this {language_} sentence with one blank:

\"\"\"{question_.question}\"\"\"

They saw only this English hint of the meaning, and had to type the missing {language_} word(s) themselves, in the
form the sentence requires:
"{question_.hint}"

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
- In "comment", explain briefly in English why the expected answer is right here, and if the learner typed another
  word, how its meaning differs.
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


def correct_answer(vocabulary_: Vocabulary, question_: TypedQuestion, answer_: str) -> Dict[str, Any]:
    response_ = get_openai_client().responses.create(model=current_model(),
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


def check_answer(vocabulary_: Vocabulary, question_: TypedQuestion,
                 answer_: str) -> Tuple[TypedCorrection, Optional[str]]:
    try:
        return normalize_correction(question_, correct_answer(vocabulary_, question_, answer_)), None
    except (JSONDecodeError, KeyError, TypeError) as error_:
        fallback_ = {"verdict": "correct" if answer_ == question_.correct_answer else "wrong_word"}
        return normalize_correction(question_, fallback_), \
            f"The correction could not be read ({type(error_).__name__}: {error_})."
