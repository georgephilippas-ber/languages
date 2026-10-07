import re
from dataclasses import dataclass
from json import loads, JSONDecodeError
from os import makedirs
from textwrap import fill
from typing import Dict, List, Optional, Tuple

from src.domain import Vocabulary
from src.library import Kind, MAX_TERMS_PER_FILE, count_terms, kind_directory, kind_file_name, kind_file_numbers, \
    kind_file_path, read_kind_file, split_entries
from src.openai_integration import get_openai_client, current_model, strip_code_fences

LINE_WIDTH: int = 120
EXAMPLE_ENTRIES: int = 2
FORMAT_VOCABULARY: Vocabulary = Vocabulary.GERMAN

TRANSLATION_LINES: Dict[Vocabulary, str] = {Vocabulary.GERMAN: "**English:** … · **French:** …",
                                            Vocabulary.ENGLISH: "**German:** … · **French:** …",
                                            Vocabulary.FRENCH: "**English:** … · **German:** …"}

EXAMPLE_TRANSLATION_LANGUAGE: Dict[Vocabulary, str] = {Vocabulary.GERMAN: "English", Vocabulary.FRENCH: "English",
                                                       Vocabulary.ENGLISH: "French"}

KIND_DESCRIPTIONS: Dict[Kind, str] = {
    Kind.VOCABULARY: "a vocabulary term (a word or a short phrase built around one word)",
    Kind.IDIOMS: "an idiom or fixed expression",
    Kind.GRAMMATICAL: "a grammatical construction, shown with a short example in the heading"}

GLOSS_LANGUAGE: Dict[Vocabulary, str] = {Vocabulary.GERMAN: "English", Vocabulary.FRENCH: "English",
                                         Vocabulary.ENGLISH: "English (a plain paraphrase)"}

BULLET_REGEXP = re.compile(r"^\s*[*-] ")


@dataclass
class DefinedEntry:
    term: str
    markdown: str
    gloss: str


@dataclass
class SavedEntry:
    term: str
    file_name: str
    terms_in_file: int


@dataclass
class SaveResult:
    saved: List[SavedEntry]
    file_name: str
    terms_in_file: int
    file_full: bool


def __format_examples(kind_: Kind) -> str:
    examples_: List[str] = []
    for source_kind_ in dict.fromkeys([kind_, Kind.VOCABULARY]):
        for file_number_ in reversed(kind_file_numbers(source_kind_, FORMAT_VOCABULARY)):
            entries_ = split_entries(read_kind_file(source_kind_, FORMAT_VOCABULARY, file_number_))
            if entries_:
                examples_.extend(entries_[-(EXAMPLE_ENTRIES - len(examples_)):])
                break
        if len(examples_) >= EXAMPLE_ENTRIES:
            break

    return "\n\n---\n\n".join(examples_)


def define_prompt(vocabulary_: Vocabulary, kind_: Kind, term_: str) -> str:
    language_ = vocabulary_.name.capitalize()

    return f"""
You are an experienced {language_} lexicographer and teacher writing entries for a learner's personal vocabulary
notebook. Write one entry for {KIND_DESCRIPTIONS[kind_]} in {language_}, as requested by the learner:

\"\"\"{term_}\"\"\"

The request may be a bare word, include an article, contain a typo, or carry a short note (for example after a dash
or in brackets) about the sense the learner means; focus on that sense, and mention the other common senses briefly.

Follow the format of these existing entries exactly (they may be in another language; adapt it to {language_}):

{__format_examples(kind_)}

Rules:
- Start with a heading line "## " + the headword. Nouns take the article in the singular where the language has
  one (in German, e.g. "das Gespür"); verbs are in the infinitive and show their objects and cases or prepositions
  (in German, e.g. "etwas (Akkusativ) abdecken / mit etwas (Dativ) abdecken"); add a common fixed phrase after " / " when it is the usual way to use the word.
- Then these paragraphs, separated by blank lines, in this order: "**CEFR:** roughly **…**.", "**Definition:**",
  "**Synonym:**", "**Grammar:**", "**Example:**" (an italic {language_} sentence, then " — " and its
  {EXAMPLE_TRANSLATION_LANGUAGE[vocabulary_]} translation in quotation marks), "Another example: …" (same shape, no
  bold label), the translation line "{TRANSLATION_LINES[vocabulary_]}", and finally "Useful nuance: …".
- Use **bold** for {language_} forms and key translations, *italics* for {language_} example phrases, as in the
  examples. Write the explanations in English.
- Never write "##" anywhere except at the start of the heading line.

Also give "gloss": the simplest {GLOSS_LANGUAGE[vocabulary_]} translation of the headword, a few words at most (e.g.
"crow" or "to cover").

Return only a JSON object, with no Markdown code fences and no other text:
{{"entry": str, "gloss": str}}"""


def __wrap_paragraph(paragraph_: str) -> str:
    lines_ = paragraph_.splitlines()
    if lines_[0].startswith("#") or any(BULLET_REGEXP.match(line_) for line_ in lines_):
        return paragraph_

    return fill(" ".join(line_.strip() for line_ in lines_), width=LINE_WIDTH, break_long_words=False,
                break_on_hyphens=False)


def normalize_entry(markdown_: str) -> str:
    text_ = strip_code_fences(markdown_).replace("\r\n", "\n").strip()
    if not text_.startswith("## "):
        raise ValueError("the entry must start with a '## ' heading")

    heading_, _, body_ = text_.partition("\n")
    heading_ = "## " + " ".join(heading_[3:].split())
    if len(heading_) <= 3:
        raise ValueError("the heading is empty")
    if "##" in heading_[3:] or "##" in body_:
        raise ValueError("'##' may appear only at the start of the heading")
    if "**Definition:**" not in body_:
        raise ValueError("the entry has no **Definition:** paragraph")

    paragraphs_ = [paragraph_.strip("\n") for paragraph_ in re.split(r"\n\s*\n", body_) if paragraph_.strip()]

    return "\n\n".join([heading_] + [__wrap_paragraph(paragraph_) for paragraph_ in paragraphs_])


def entry_term(markdown_: str) -> str:
    return markdown_.partition("\n")[0][3:].strip()


def __demo_entry(vocabulary_: Vocabulary, term_: str) -> Dict[str, str]:
    translation_line_ = TRANSLATION_LINES[vocabulary_].replace("…", "(demo)")

    return {"entry": f"""## {term_}

**CEFR:** roughly **B2**.

**Definition:** (demo: a placeholder entry written without calling the API.)

**Synonym:** **(demo)**

**Grammar:** (demo)

**Example:** *(demo)* — "(demo)"

{translation_line_}

Useful nuance: (demo)""", "gloss": "(demo)"}


def define_entry(vocabulary_: Vocabulary, kind_: Kind, term_: str, demo_: bool = False) -> DefinedEntry:
    if demo_:
        response_json_ = __demo_entry(vocabulary_, term_)
    else:
        response_ = get_openai_client().responses.create(model=current_model(),
                                                         input=define_prompt(vocabulary_, kind_, term_))
        response_json_ = loads(strip_code_fences(response_.output_text))
        if not isinstance(response_json_, dict) or not isinstance(response_json_.get("entry"), str):
            raise TypeError("the response has no entry")

    markdown_ = normalize_entry(response_json_["entry"])

    return DefinedEntry(term=entry_term(markdown_), markdown=markdown_, gloss=str(response_json_.get("gloss") or ""))


def check_definition(vocabulary_: Vocabulary, kind_: Kind, term_: str,
                     demo_: bool = False) -> Tuple[Optional[DefinedEntry], Optional[str]]:
    try:
        return define_entry(vocabulary_, kind_, term_, demo_), None
    except (JSONDecodeError, KeyError, TypeError, ValueError) as error_:
        return None, f"The entry could not be read ({type(error_).__name__}: {error_})."


def target_file_number(kind_: Kind, vocabulary_: Vocabulary) -> int:
    file_numbers_ = kind_file_numbers(kind_, vocabulary_)
    if not file_numbers_:
        return 1

    latest_ = file_numbers_[-1]
    if count_terms(read_kind_file(kind_, vocabulary_, latest_)) >= MAX_TERMS_PER_FILE:
        return latest_ + 1

    return latest_


def __append(kind_: Kind, vocabulary_: Vocabulary, file_number_: int, markdown_: str) -> int:
    text_ = read_kind_file(kind_, vocabulary_, file_number_).rstrip("\n")
    text_ = (text_ + "\n\n" if text_ else "") + markdown_ + "\n"

    makedirs(kind_directory(kind_, vocabulary_), exist_ok=True)
    with open(kind_file_path(kind_, vocabulary_, file_number_), "w", encoding="utf-8") as file_:
        file_.write(text_)

    return count_terms(text_)


def save_entries(vocabulary_: Vocabulary, kind_: Kind, markdowns_: List[str], demo_: bool = False) -> SaveResult:
    entries_ = [normalize_entry(markdown_) for markdown_ in markdowns_]

    saved_: List[SavedEntry] = []
    file_number_ = target_file_number(kind_, vocabulary_)
    terms_in_file_ = count_terms(read_kind_file(kind_, vocabulary_, file_number_))
    for markdown_ in entries_:
        if terms_in_file_ >= MAX_TERMS_PER_FILE:
            file_number_ += 1
            terms_in_file_ = 0
        terms_in_file_ = terms_in_file_ + 1 if demo_ else __append(kind_, vocabulary_, file_number_, markdown_)
        saved_.append(SavedEntry(term=entry_term(markdown_), file_name=kind_file_name(vocabulary_, file_number_),
                                 terms_in_file=terms_in_file_))

    return SaveResult(saved=saved_, file_name=kind_file_name(vocabulary_, file_number_), terms_in_file=terms_in_file_,
                      file_full=terms_in_file_ >= MAX_TERMS_PER_FILE)
