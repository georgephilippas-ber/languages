from dataclasses import dataclass
from json import loads, JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple

from src.configuration import MODEL
from src.domain import Vocabulary
from src.openai_integration import get_openai_client, strip_code_fences

MAX_NOTES: int = 4

PARTNER_LANGUAGE: Dict[Vocabulary, str] = {Vocabulary.GERMAN: "English", Vocabulary.FRENCH: "English",
                                           Vocabulary.ENGLISH: "German"}


@dataclass
class Translation:
    source_language: str
    target_language: str
    translation: str
    notes: List[str]


def translate_prompt(vocabulary_: Vocabulary, phrase_: str) -> str:
    language_ = vocabulary_.name.capitalize()
    partner_ = PARTNER_LANGUAGE[vocabulary_]

    return f"""
You are an experienced {language_} teacher helping a learner. Translate this phrase:

\"\"\"{phrase_}\"\"\"

It is most likely {language_}: then translate it into {partner_}. If it is {partner_} instead, translate it into
{language_}; if it is in any other language, translate it into {language_}. Give the natural, idiomatic translation;
add a second, more literal one after " / " only when the two differ a lot.

Then add up to {MAX_NOTES} succinct linguistic or grammar notes in English on the {language_} side, each a single short
sentence: for example case or preposition government, verb forms, word order, gender, register, false friends, or a
fixed expression. Only notes a learner would find useful; none for trivial phrases. Use **bold** for {language_}
forms and *italics* for {language_} phrases.

Return only a JSON object, with no Markdown code fences and no other text:
{{"source_language": str, "target_language": str, "translation": str, "notes": [str]}}"""


def __demo_translation(vocabulary_: Vocabulary, phrase_: str) -> Dict[str, Any]:
    return {"source_language": vocabulary_.name.capitalize(), "target_language": PARTNER_LANGUAGE[vocabulary_],
            "translation": f"(demo) {phrase_}", "notes": ["(demo: a placeholder written without calling the API.)"]}


def normalize_translation(vocabulary_: Vocabulary, response_json_: Any) -> Translation:
    if not isinstance(response_json_, dict) or not isinstance(response_json_.get("translation"), str):
        raise TypeError("the response has no translation")
    translation_ = response_json_["translation"].strip()
    if not translation_:
        raise ValueError("the translation is empty")
    notes_ = response_json_.get("notes") or []
    if not isinstance(notes_, list):
        notes_ = [notes_]

    return Translation(source_language=str(response_json_.get("source_language") or vocabulary_.name.capitalize()),
                       target_language=str(response_json_.get("target_language") or PARTNER_LANGUAGE[vocabulary_]),
                       translation=translation_,
                       notes=[str(note_).strip() for note_ in notes_ if str(note_).strip()][:MAX_NOTES])


def translate_phrase(vocabulary_: Vocabulary, phrase_: str, demo_: bool = False) -> Translation:
    if demo_:
        response_json_ = __demo_translation(vocabulary_, phrase_)
    else:
        response_ = get_openai_client().responses.create(model=MODEL, input=translate_prompt(vocabulary_, phrase_))
        response_json_ = loads(strip_code_fences(response_.output_text))

    return normalize_translation(vocabulary_, response_json_)


def check_translation(vocabulary_: Vocabulary, phrase_: str,
                      demo_: bool = False) -> Tuple[Optional[Translation], Optional[str]]:
    try:
        return translate_phrase(vocabulary_, phrase_, demo_), None
    except (JSONDecodeError, KeyError, TypeError, ValueError) as error_:
        return None, f"The translation could not be read ({type(error_).__name__}: {error_})."
