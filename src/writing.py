import re
from dataclasses import dataclass
from json import loads, JSONDecodeError
from os.path import basename
from random import sample
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.configuration import MODEL
from src.domain import Vocabulary, Correction
from src.openai_integration import get_openai_client, strip_code_fences
from src.parser import get_vocabulary_file_numbers, get_vocabulary_file_path

WORDS_PER_SENTENCE: int = 2

TRANSLATION_LANGUAGE: Dict[Vocabulary, str] = {Vocabulary.GERMAN: "English", Vocabulary.FRENCH: "English",
                                               Vocabulary.ENGLISH: "German"}

HINT_LABELS: List[str] = ["English", "German", "French"]

DEMO_IGNORED_WORDS: List[str] = ["etwas", "jemandem", "jemanden", "jemand", "jemandes", "sich", "einer", "einem",
                                 "eines", "something", "someone", "quelque", "chose", "quelqu'un"]


@dataclass
class IndexedTerm:
    term: str
    file_name: str
    hint: str


@dataclass
class TermCheck:
    term: str
    used: bool
    used_correctly: bool
    comment: str


@dataclass
class WritingCorrection:
    is_correct: bool
    minimal_correction: str
    natural_version: str
    natural_explanation: str
    translation: str
    terms: List[TermCheck]
    corrections: List[Correction]
    feedback: str


def __hint(entry_text_: str) -> str:
    for label_ in HINT_LABELS:
        match_ = re.search(rf"^\*\*{label_}:\*\*(.*?)(?:\n\s*\n|\Z)", entry_text_, flags=re.M | re.S)
        if match_ is not None:
            meanings_ = re.sub(r"\*+", "", " ".join(match_.group(1).split()).split("·")[0].split(";")[0]).strip()
            return " / ".join(meaning_.strip() for meaning_ in meanings_.split(" / ")[:3])

    return ""


def index_vocabulary(vocabulary_: Vocabulary, file_numbers_: Optional[List[int]] = None) -> List[IndexedTerm]:
    index_: List[IndexedTerm] = []
    file_numbers_ = file_numbers_ if file_numbers_ is not None else get_vocabulary_file_numbers(vocabulary_)

    for file_number_ in file_numbers_:
        file_path_ = get_vocabulary_file_path(vocabulary_, file_number_)
        with open(file_path_, "r", encoding="utf-8") as vocabulary_file_:
            text_ = vocabulary_file_.read()

        for chunk_ in re.split(r"^## ", text_, flags=re.M)[1:]:
            heading_, _, body_ = chunk_.partition("\n")
            index_.append(IndexedTerm(term=heading_.strip(), file_name=basename(file_path_),
                                      hint=__hint(body_)))

    return index_


def pick_word_pairs(index_: List[IndexedTerm], rounds_: int) -> List[Tuple[IndexedTerm, ...]]:
    if len(index_) >= rounds_ * WORDS_PER_SENTENCE:
        picked_ = sample(index_, rounds_ * WORDS_PER_SENTENCE)
        return [tuple(picked_[i_:i_ + WORDS_PER_SENTENCE]) for i_ in range(0, len(picked_), WORDS_PER_SENTENCE)]

    return [tuple(sample(index_, WORDS_PER_SENTENCE)) for _ in range(rounds_)]


def correction_prompt(vocabulary_: Vocabulary, terms_: Sequence[IndexedTerm], sentence_: str) -> str:
    language_ = vocabulary_.name.capitalize()
    terms_list_ = "\n".join(f'{i_}. "{term_.term}"' for i_, term_ in enumerate(terms_, start=1))

    return f"""
You are an experienced {language_} teacher. A learner was asked to write one sentence in {language_}
that uses all of the following vocabulary terms, in any grammatically appropriate form:

{terms_list_}

The learner's sentence:
\"\"\"{sentence_}\"\"\"

Tasks:
- Write two corrected versions of the learner's text:
  (a) "minimal_correction": fix only actual errors (grammar, spelling, punctuation, word order, and words that are
      wrong). Keep the learner's structure and word choices wherever they are correct, so that the learner can see
      exactly what was wrong. If the text has no errors, return it unchanged.
  (b) "natural_version": how a native {language_} speaker would naturally express the same idea, keeping both
      terms and the learner's intended meaning. Use idiomatic word choice and natural collocations, and restructure
      freely where the learner's wording is grammatical but not what a native speaker would say (e.g. a verb used
      with an object or in a sense it does not normally take). If the learner's text is already natural, return it
      unchanged.
- In "natural_explanation", explain briefly in English what makes the natural version more natural than the minimal
  correction, focusing on word choice and collocations. Use an empty string if both versions are identical.
- List every change in the minimal correction in "corrections", each with a short explanation in English.
- For each term, check whether the learner used it, and whether it is used correctly: in meaning, form,
  construction (e.g. case, preposition, reflexive pronoun), and with the kind of object or context native speakers
  use it with. Judge each term only on its own use; errors elsewhere in the text must not count against it.
- Translate the natural version into {TRANSLATION_LANGUAGE[vocabulary_]}.
- Give one or two sentences of honest, encouraging overall feedback in English.

Return only a JSON object, with no Markdown code fences and no other text:
{{
    "minimal_correction": str,
    "natural_version": str,
    "natural_explanation": str,
    "translation": str,
    "is_correct": bool,
    "terms": [
        {{"term": str, "used": bool, "used_correctly": bool, "comment": str}}
    ],
    "corrections": [
        {{"original": str, "corrected": str, "explanation": str}}
    ],
    "feedback": str
}}

"is_correct" must be true only if the minimal correction needed no changes at all. "terms" must contain one object
per term above, in the same order."""


def __demo_used(term_: str, sentence_: str) -> bool:
    words_ = [word_ for word_ in re.findall(r"[^\W\d_]+", re.sub(r"\([^)]*\)", "", term_.split(" / ")[0]).lower())
              if word_ not in DEMO_IGNORED_WORDS and len(word_) > 2]
    sentence_ = sentence_.lower()

    return bool(words_) and any(word_[:max(4, len(word_) - 2)] in sentence_ for word_ in words_)


def __demo_correction(terms_: Sequence[IndexedTerm], sentence_: str) -> Dict[str, Any]:
    checks_ = [{"term": term_.term, "used": __demo_used(term_.term, sentence_),
                "used_correctly": __demo_used(term_.term, sentence_),
                "comment": "" if __demo_used(term_.term, sentence_) else "(demo: the term was not found)"}
               for term_ in terms_]

    return {"minimal_correction": sentence_, "natural_version": sentence_, "natural_explanation": "",
            "translation": "(demo: no translation without the API)",
            "is_correct": all(check_["used"] for check_ in checks_), "terms": checks_, "corrections": [],
            "feedback": "(demo: the sentence was checked only for the two terms, without calling the API)"}


def correct_sentence(vocabulary_: Vocabulary, terms_: Sequence[IndexedTerm], sentence_: str,
                     demo_: bool = False) -> Dict[str, Any]:
    if demo_:
        return __demo_correction(terms_, sentence_)

    response_ = get_openai_client().responses.create(model=MODEL,
                                                     input=correction_prompt(vocabulary_, terms_, sentence_))
    correction_ = loads(strip_code_fences(response_.output_text))
    if not isinstance(correction_, dict):
        raise TypeError("the response is not a JSON object")

    return correction_


def normalize_correction(sentence_: str, terms_: Sequence[IndexedTerm],
                         correction_: Dict[str, Any]) -> WritingCorrection:
    minimal_ = str(correction_.get("minimal_correction") or sentence_)
    natural_ = str(correction_.get("natural_version") or minimal_)
    terms_json_ = correction_.get("terms", [])
    terms_json_ = terms_json_ if isinstance(terms_json_, list) else []
    corrections_ = correction_.get("corrections", [])
    corrections_ = [item_ for item_ in corrections_ if isinstance(item_, dict)] if isinstance(corrections_, list) \
        else []

    checks_: List[TermCheck] = []
    for i_, term_ in enumerate(terms_):
        term_json_ = terms_json_[i_] if i_ < len(terms_json_) and isinstance(terms_json_[i_], dict) else {}
        checks_.append(TermCheck(term=term_.term, used=bool(term_json_.get("used")),
                                 used_correctly=bool(term_json_.get("used_correctly")),
                                 comment=str(term_json_.get("comment") or "")))

    return WritingCorrection(
        is_correct=bool(correction_.get("is_correct")) and minimal_.strip() == sentence_.strip(),
        minimal_correction=minimal_,
        natural_version=natural_,
        natural_explanation=str(correction_.get("natural_explanation") or ""),
        translation=str(correction_.get("translation") or ""),
        terms=checks_,
        corrections=[Correction(original=str(item_.get("original", "")), corrected=str(item_.get("corrected", "")),
                                explanation=str(item_.get("explanation") or "")) for item_ in corrections_],
        feedback=str(correction_.get("feedback") or ""))


def check_sentence(vocabulary_: Vocabulary, terms_: Sequence[IndexedTerm], sentence_: str,
                   demo_: bool = False) -> Tuple[Optional[WritingCorrection], Optional[str]]:
    try:
        return normalize_correction(sentence_, terms_, correct_sentence(vocabulary_, terms_, sentence_, demo_)), None
    except (JSONDecodeError, KeyError, TypeError) as error_:
        return None, f"The correction could not be read ({type(error_).__name__}: {error_})."
