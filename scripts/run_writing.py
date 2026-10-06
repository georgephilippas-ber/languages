#!/usr/local/bin/python3
"""Sentence-writing exercise: for each round, two terms are picked from all of a language's vocabulary files, the
learner writes one sentence using both, and the model corrects and translates it.

    ./scripts/run_writing.py [questions_number] [-L LANGUAGE] [-f N]

Uses the same parameter scheme as run_vocabulary.py for the language and the number of questions.
"""
import argparse
import re
import sys
from dataclasses import dataclass
from json import loads, JSONDecodeError
from os.path import abspath, basename, dirname
from random import sample
from shutil import get_terminal_size
from textwrap import fill
from typing import Any, Dict, List, Optional, Tuple

# The repository root, so that src.* can be imported when this script is run from scripts/.
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from run_vocabulary import positive_integer, vocabulary, language_code, LANGUAGE_CODES, file_number_or_all, \
    resolve_file_numbers, file_names, ALL_FILES, LATEST_FILE
from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_VOCABULARY, LATEST_FILES_NUMBER
from src.domain import Vocabulary
from src.openai_integration import get_openai_client
from src.parser import get_vocabulary_file_numbers, get_vocabulary_file_path

MODEL: str = "gpt-6-sol"
WORDS_PER_SENTENCE: int = 2
QUIT: str = "quit"

# The language the learner's corrected sentence is translated into.
TRANSLATION_LANGUAGE: Dict[Vocabulary, str] = {Vocabulary.GERMAN: "English", Vocabulary.FRENCH: "English",
                                               Vocabulary.ENGLISH: "German"}

# ANSI styles, only used when printing to a terminal.
USE_COLOURS: bool = sys.stdout.isatty()
BOLD, DIM, GREEN, RED, YELLOW, RESET = ("\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[33m", "\033[0m") \
    if USE_COLOURS else ("", "", "", "", "", "")
ITALIC, ITALIC_OFF = ("\033[3m", "\033[23m") if USE_COLOURS else ("", "")
LABEL_WIDTH: int = 13
HINT_COLUMN_LIMIT: int = 40  # longest headword for which hints are shown in a column next to the terms


@dataclass
class IndexedTerm:
    term: str
    file_name: str
    hint: str  # short meaning shown next to the term: English, or German / French for English terms; may be empty


# ---------------------------------------------------------------------------------------------------------------------
# Indexing: done once, before the first round.
# ---------------------------------------------------------------------------------------------------------------------

# Translation labels to take the hint from, in order of preference (English entries have German or French instead).
HINT_LABELS: List[str] = ["English", "German", "French"]


def __hint(entry_text_: str) -> str:
    """The first few meanings from an entry's translation paragraph, without Markdown or a second translation."""
    for label_ in HINT_LABELS:
        match_ = re.search(rf"^\*\*{label_}:\*\*(.*?)(?:\n\s*\n|\Z)", entry_text_, flags=re.M | re.S)
        if match_ is not None:
            meanings_ = re.sub(r"\*+", "", " ".join(match_.group(1).split()).split("·")[0].split(";")[0]).strip()
            return " / ".join(meaning_.strip() for meaning_ in meanings_.split(" / ")[:3])

    return ""


def index_vocabulary(vocabulary_: Vocabulary, file_numbers_: Optional[List[int]] = None) -> List[IndexedTerm]:
    """Every '## ' entry of the given files, or of all of the language's files when file_numbers_ is None. Text
    before a file's first heading (titles, introductions) is not an entry."""
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
    """All rounds' words are picked up front. When there are enough terms, no term appears twice in a session."""
    if len(index_) >= rounds_ * WORDS_PER_SENTENCE:
        picked_ = sample(index_, rounds_ * WORDS_PER_SENTENCE)
        return [tuple(picked_[i_:i_ + WORDS_PER_SENTENCE]) for i_ in range(0, len(picked_), WORDS_PER_SENTENCE)]

    return [tuple(sample(index_, WORDS_PER_SENTENCE)) for _ in range(rounds_)]


# ---------------------------------------------------------------------------------------------------------------------
# Correction
# ---------------------------------------------------------------------------------------------------------------------

def correction_prompt(vocabulary_: Vocabulary, terms_: Tuple[IndexedTerm, ...], sentence_: str) -> str:
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


def __strip_code_fences(text_: str) -> str:
    text_ = text_.strip()
    if text_.startswith("```"):
        text_ = text_.split("\n", 1)[1] if "\n" in text_ else ""
        text_ = text_.rsplit("```", 1)[0]

    return text_.strip()


def correct_sentence(client_, vocabulary_: Vocabulary, terms_: Tuple[IndexedTerm, ...], sentence_: str) -> \
        Dict[str, Any]:
    response_ = client_.responses.create(model=MODEL, input=correction_prompt(vocabulary_, terms_, sentence_))
    correction_ = loads(__strip_code_fences(response_.output_text))
    if not isinstance(correction_, dict):
        raise TypeError("the response is not a JSON object")

    return correction_


# ---------------------------------------------------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------------------------------------------------

def __style(text_: str, *styles_: str) -> str:
    return "".join(styles_) + text_ + RESET if styles_ and USE_COLOURS else text_


def __italic(text_: str) -> str:
    return ITALIC + text_ + ITALIC_OFF


def __width() -> int:
    return min(get_terminal_size((100, 24)).columns, 100)


def __labelled(label_: str, text_: str, *styles_: str) -> str:
    indent_ = " " * (2 + LABEL_WIDTH)
    wrapped_ = fill(text_, width=__width(), initial_indent=indent_, subsequent_indent=indent_)[len(indent_):]

    return "  " + __style(label_.ljust(LABEL_WIDTH), DIM) + __style(wrapped_, *styles_)


def __print_task(round_: int, rounds_: int, vocabulary_: Vocabulary, terms_: Tuple[IndexedTerm, ...]):
    print(__style("─" * __width(), DIM))
    print(__style(f"Sentence {round_} of {rounds_}", BOLD))
    print()
    print(f"Write one sentence in {vocabulary_.name.capitalize()} that uses both of these words:")
    print()
    term_width_ = max(len(term_.term) for term_ in terms_)
    for term_ in terms_:
        if term_width_ <= HINT_COLUMN_LIMIT:
            padding_ = " " * (term_width_ - len(term_.term))
            print(f"  • {__italic(term_.term)}{padding_}  {__style(term_.hint, DIM)}".rstrip())
        else:
            # Long headwords (several constructions) would push the hints far right: put them underneath instead.
            print(f"  • {__italic(term_.term)}")
            if term_.hint:
                print("    " + __style(term_.hint, DIM))
    print()


def __print_correction(sentence_: str, correction_: Dict[str, Any], terms_: Tuple[IndexedTerm, ...]) -> bool:
    """Returns whether the sentence was correct as written."""
    minimal_ = str(correction_.get("minimal_correction") or sentence_)
    natural_ = str(correction_.get("natural_version") or minimal_)
    is_correct_ = bool(correction_.get("is_correct")) and minimal_.strip() == sentence_.strip()

    print(__style("✓ Correct!", BOLD, GREEN) if is_correct_ else __style("✎ Corrected", BOLD, YELLOW))
    print()
    if is_correct_:
        print(__labelled("Yours", sentence_))
    else:
        print(__labelled("Yours", sentence_, DIM))
        print(__labelled("Minimal fix", minimal_))
    if natural_.strip() != minimal_.strip():
        print(__labelled("Natural", natural_, GREEN))
    else:
        print(__labelled("Natural", "(already natural)", DIM))
    print(__labelled("Translation", str(correction_.get("translation", ""))))
    print()

    terms_json_ = correction_.get("terms", [])
    terms_json_ = terms_json_ if isinstance(terms_json_, list) else []
    term_width_ = max(len(term_.term) for term_ in terms_)
    print("  " + __style("Words", DIM))
    for i_, term_ in enumerate(terms_):
        term_json_ = terms_json_[i_] if i_ < len(terms_json_) and isinstance(terms_json_[i_], dict) else {}
        used_, used_correctly_ = bool(term_json_.get("used")), bool(term_json_.get("used_correctly"))

        if used_ and used_correctly_:
            mark_, status_, styles_ = "✓", "used correctly", (GREEN,)
        elif used_:
            mark_, status_, styles_ = "~", "used, but not quite right", (YELLOW,)
        else:
            mark_, status_, styles_ = "✗", "not used", (RED,)

        if term_width_ <= HINT_COLUMN_LIMIT:
            padding_ = " " * (term_width_ - len(term_.term))
            print("  " + __style(f"{mark_} {__italic(term_.term)}{padding_}  {status_}", *styles_))
            indent_ = " " * (6 + term_width_)
        else:
            print("  " + __style(f"{mark_} {__italic(term_.term)}", *styles_))
            print("    " + __style(status_, *styles_))
            indent_ = " " * 4
        comment_ = str(term_json_.get("comment") or "")
        if comment_ and not (used_ and used_correctly_):
            print(fill(comment_, width=__width(), initial_indent=indent_, subsequent_indent=indent_))
    print()

    corrections_ = correction_.get("corrections", [])
    corrections_ = [item_ for item_ in corrections_ if isinstance(item_, dict)] if isinstance(corrections_, list) else []
    if corrections_ and not is_correct_:
        print("  " + __style("Corrections", DIM))
        for item_ in corrections_:
            print(f"  • {__style(str(item_.get('original', '')), RED)} → "
                  f"{__style(str(item_.get('corrected', '')), GREEN)}")
            if item_.get("explanation"):
                print(fill(str(item_["explanation"]), width=__width(), initial_indent="    ",
                           subsequent_indent="    "))
        print()

    natural_explanation_ = str(correction_.get("natural_explanation") or "")
    if natural_explanation_ and natural_.strip() != minimal_.strip():
        print("  " + __style("Why the natural version", DIM))
        print(fill(natural_explanation_, width=__width(), initial_indent="    ", subsequent_indent="    "))
        print()

    if correction_.get("feedback"):
        print(fill(str(correction_["feedback"]), width=__width()))
        print()

    return is_correct_


def writing_exercise(vocabulary_: Vocabulary, rounds_: int, file_numbers_: Optional[List[int]] = None):
    """file_numbers_ selects the files the words come from; None uses all of the language's files."""
    # Indexing and picking every round's words happen once, before the first round.
    index_ = index_vocabulary(vocabulary_, file_numbers_)
    if len(index_) < WORDS_PER_SENTENCE:
        print(f"Not enough {vocabulary_.name.capitalize()} terms for this exercise.")
        return

    word_pairs_ = pick_word_pairs(index_, rounds_)
    file_numbers_ = file_numbers_ if file_numbers_ is not None else get_vocabulary_file_numbers(vocabulary_)
    source_ = file_names(vocabulary_, file_numbers_)
    print(f"Picking words from {len(index_)} {vocabulary_.name.capitalize()} term{'s' if len(index_) != 1 else ''} "
          f"in {source_}. Type '{QUIT}' to stop, or press Enter to skip a sentence.")
    print()

    client_ = get_openai_client()
    correct_, answered_ = 0, 0

    for round_, terms_ in enumerate(word_pairs_, start=1):
        __print_task(round_, len(word_pairs_), vocabulary_, terms_)

        sentence_ = input("Your sentence: ").strip()
        print()
        if sentence_.lower() == QUIT:
            break
        if not sentence_:
            print(__style("Skipped.", DIM))
            print()
            continue

        print(__style("Correcting...", DIM))
        try:
            correction_ = correct_sentence(client_, vocabulary_, terms_, sentence_)
        except (JSONDecodeError, KeyError, TypeError) as error_:
            print(f"The correction could not be read ({type(error_).__name__}: {error_}).")
            print()
            continue
        print()

        answered_ += 1
        correct_ += __print_correction(sentence_, correction_, terms_)

    if answered_ > 0:
        print(__style("─" * __width(), DIM))
        print(__style(f"Correct as written: {correct_}/{answered_} sentence{'s' if answered_ != 1 else ''}", BOLD))
        print()


EXAMPLES: List[Tuple[str, str]] = [
    ("", f"{DEFAULT_NUMBER_OF_QUESTIONS} sentences in {DEFAULT_VOCABULARY.name.capitalize()}, words from the latest "
         f"two files"),
    ("2 -L FR", "2 sentences in French, words from the latest two files"),
    ("-f 2", f"{DEFAULT_NUMBER_OF_QUESTIONS} sentences with words from german-2.md"),
    (f"6 -f {ALL_FILES}", "6 sentences with words from all German files"),
]

if __name__ == "__main__":
    command_line_argument_parser_ = argparse.ArgumentParser(
        description=fill("Sentence-writing exercise. Each round picks two terms from a language's vocabulary "
                         "files (by default the latest two); you write one sentence that uses both, and you get a "
                         "minimal fix of your errors, a natural version as a native speaker would say it, a "
                         "translation, and a check of each term. Press Enter to skip a sentence, or type 'quit' to "
                         "stop.", width=90),
        epilog="examples:\n" +
               "\n".join(f"  %(prog)s {example_:<{max(len(example_) for example_, _ in EXAMPLES)}}  {text_}"
                         for example_, text_ in EXAMPLES) +
               "\n\nfor the multiple choice quiz, Anki decks, and vocabulary info, see './scripts/run_vocabulary.py --help'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    command_line_argument_parser_.add_argument("questions_number", nargs="?", default=DEFAULT_NUMBER_OF_QUESTIONS,
                                               type=positive_integer,
                                               help=f"number of sentences (default: {DEFAULT_NUMBER_OF_QUESTIONS})")
    command_line_argument_parser_.add_argument("-L", "--language", dest="vocabulary", default=DEFAULT_VOCABULARY,
                                               type=vocabulary, metavar="LANGUAGE",
                                               help=f"{', '.join(LANGUAGE_CODES)} "
                                                    f"(default: {language_code(DEFAULT_VOCABULARY)})")
    command_line_argument_parser_.add_argument("-f", "--file", dest="file_number", default=None,
                                               type=file_number_or_all, metavar="N",
                                               help=f"only use words from the vocabulary file <language>-N.md; "
                                                    f"'{LATEST_FILE}' for the latest {LATEST_FILES_NUMBER} files, "
                                                    f"i.e. the highest N and N - 1, or '{ALL_FILES}' for all files "
                                                    f"(default: {LATEST_FILE})")
    arguments_ = command_line_argument_parser_.parse_args()
    file_numbers_ = resolve_file_numbers(command_line_argument_parser_, "-f/--file", arguments_.vocabulary,
                                         arguments_.file_number)

    try:
        writing_exercise(arguments_.vocabulary, arguments_.questions_number, file_numbers_)
    except KeyboardInterrupt:
        # Ctrl+C leaves the cursor after "^C" on the current line: end that line, then leave an empty one.
        print()
        print()
    finally:
        print("Goodbye!")
