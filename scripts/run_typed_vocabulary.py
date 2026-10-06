#!/usr/local/bin/python3

import argparse
import sys
from dataclasses import dataclass
from json import dumps, loads, JSONDecodeError
from os.path import abspath, basename, dirname
from shutil import get_terminal_size
from textwrap import fill
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from run_vocabulary import positive_integer, vocabulary, cefr_level, language_code, LANGUAGE_CODES, \
    file_number_or_all, resolve_file_numbers, file_names, ALL_FILES, LATEST_FILE, REVISE_COMMAND, \
    REVISION_QUESTIONS_NUMBER
from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_VOCABULARY, DEFAULT_CEFR_LEVEL, UNSEEN_ALPHA, \
    LATEST_FILES_NUMBER, SECONDS_PER_QUESTION
from src.domain import Vocabulary, Entry, CEFRLevel
from src.launcher import time_summary
from src.parser import get_vocabulary_file_numbers

MODEL: str = "gpt-6-sol"
BLANK: str = "_____"
QUIT: str = "q"
ALTERNATIVES_PER_QUESTION: int = 3

CHOICES_LANGUAGE: Dict[Vocabulary, str] = {Vocabulary.GERMAN: "English", Vocabulary.FRENCH: "English",
                                           Vocabulary.ENGLISH: "German"}

QUESTION_KEYS: List[str] = ["question", "choices", "choices_translations", "correct_choice", "correct_answer",
                            "complete_sentence", "english_translation"]
VERDICTS: List[str] = ["correct", "wrong_form", "wrong_word"]

USE_COLOURS: bool = sys.stdout.isatty()
BOLD, DIM, GREEN, RED, YELLOW, RESET = ("\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[33m", "\033[0m") \
    if USE_COLOURS else ("", "", "", "", "", "")
ITALIC, ITALIC_OFF = ("\033[3m", "\033[23m") if USE_COLOURS else ("", "")
LABEL_WIDTH: int = 13


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


def __strip_code_fences(text_: str) -> str:
    text_ = text_.strip()
    if text_.startswith("```"):
        text_ = text_.split("\n", 1)[1] if "\n" in text_ else ""
        text_ = text_.rsplit("```", 1)[0]

    return text_.strip()


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
    response_json_ = loads(__strip_code_fences(response_text_))
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


def construct_questions(client_, vocabulary_: Vocabulary, cefr_level_: CEFRLevel, questions_number_: int,
                        file_numbers_: List[int], demo_: bool = False) -> List[TypedQuestion]:
    from src.database import retrieve_used_terms, insert_term
    from src.openai_integration import sample_, sample_alternatives_
    from src.parser import parse_vocabulary_to_dict

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
        response_ = client_.responses.create(model=MODEL,
                                             input=questions_prompt(entries_alternatives_, vocabulary_, cefr_level_))
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


def correct_answer(client_, vocabulary_: Vocabulary, question_: TypedQuestion, answer_: str,
                   demo_: bool = False) -> Dict[str, Any]:
    if demo_:
        verdict_ = "correct" if answer_ == question_.correct_answer else \
            "wrong_form" if answer_.lower() == question_.correct_answer.lower() else "wrong_word"
        return {"verdict": verdict_, "corrected_answer": question_.correct_answer, "errors": [],
                "comment": "(demo: compared with the expected answer, without calling the API)", "suggestions": []}

    response_ = client_.responses.create(model=MODEL, input=correction_prompt(vocabulary_, question_, answer_))
    correction_ = loads(__strip_code_fences(response_.output_text))
    if not isinstance(correction_, dict):
        raise TypeError("the response is not a JSON object")

    return correction_


def __style(text_: str, *styles_: str) -> str:
    return "".join(styles_) + text_ + RESET if styles_ and USE_COLOURS else text_


def __italic(text_: str) -> str:
    return ITALIC + text_ + ITALIC_OFF


def __letter(index_: int) -> str:
    return chr(ord('A') + index_)


def __width() -> int:
    return min(get_terminal_size((100, 24)).columns, 100)


def __labelled(label_: str, text_: str, *styles_: str) -> str:
    indent_ = " " * (2 + LABEL_WIDTH)
    wrapped_ = fill(text_, width=__width(), initial_indent=indent_, subsequent_indent=indent_)[len(indent_):]

    return "  " + __style(label_.ljust(LABEL_WIDTH), DIM) + __style(wrapped_, *styles_)


def __print_question(index_: int, total_: int, vocabulary_: Vocabulary, question_: TypedQuestion):
    print(__style("─" * __width(), DIM))
    print(__style(f"Question {index_ + 1} of {total_}", BOLD) + __style(f"  ·  {SECONDS_PER_QUESTION} s", DIM))
    print()
    print(fill(question_.question, width=__width()))
    print()
    print("  " + __style(f"Choices ({CHOICES_LANGUAGE[vocabulary_]})", DIM))
    for choice_index_, translation_ in enumerate(question_.choices_translations):
        print(f"  {__letter(choice_index_)}. {translation_}")
    print()


def __print_correction(question_: TypedQuestion, answer_: str, correction_: Dict[str, Any]) -> str:
    verdict_ = str(correction_.get("verdict", "")).strip()
    verdict_ = verdict_ if verdict_ in VERDICTS else "wrong_word"
    corrected_ = str(correction_.get("corrected_answer") or question_.correct_answer)

    if verdict_ == "correct":
        print(__style("✓ Correct!", BOLD, GREEN))
    elif verdict_ == "wrong_form":
        print(__style("~ Right word, wrong form", BOLD, YELLOW))
    else:
        print(__style("✗ Incorrect", BOLD, RED))
    print()

    print(__labelled("Yours", question_.question.replace(BLANK, __italic(answer_)),
                     *(() if verdict_ == "correct" else (DIM,))))
    if verdict_ != "correct":
        print(__labelled("Corrected", __italic(corrected_), GREEN))
    if corrected_.strip() != question_.correct_answer.strip():
        print(__labelled("Expected", __italic(question_.correct_answer)))
    print(__labelled("Sentence", question_.complete_sentence))
    print(__labelled("Translation", question_.english_translation))
    print()

    print("  " + __style("Choices", DIM))
    choice_width_ = max(len(choice_) for choice_ in question_.choices)
    for choice_index_, (choice_, translation_) in enumerate(zip(question_.choices, question_.choices_translations)):
        padding_ = " " * (choice_width_ - len(choice_))
        line_ = f"{__letter(choice_index_)}  {__italic(choice_)}{padding_}  {translation_}".rstrip()
        mark_, styles_ = ("✓", (GREEN,)) if choice_index_ == question_.correct_choice else (" ", (DIM,))
        print("  " + __style(f"{mark_} {line_}", *styles_))
    print()

    errors_ = correction_.get("errors", [])
    errors_ = [item_ for item_ in errors_ if isinstance(item_, dict)] if isinstance(errors_, list) else []
    if errors_ and verdict_ != "correct":
        print("  " + __style("Errors", DIM))
        for item_ in errors_:
            print(f"  • {__style(str(item_.get('original', '')), RED)} → "
                  f"{__style(str(item_.get('corrected', '')), GREEN)}")
            if item_.get("explanation"):
                print(fill(str(item_["explanation"]), width=__width(), initial_indent="    ",
                           subsequent_indent="    "))
        print()

    if correction_.get("comment"):
        print(fill(str(correction_["comment"]), width=__width()))
        print()

    suggestions_ = correction_.get("suggestions", [])
    suggestions_ = [str(item_) for item_ in suggestions_ if item_] if isinstance(suggestions_, list) else []
    if suggestions_:
        print("  " + __style("Suggestions", DIM))
        for suggestion_ in suggestions_:
            print(fill(suggestion_, width=__width(), initial_indent="  • ", subsequent_indent="    "))
        print()

    return verdict_


def run_typed_quiz(vocabulary_: Vocabulary, cefr_level_: CEFRLevel, questions_number_: int,
                   file_numbers_: List[int], demo_: bool = False):
    print(f"Constructing {questions_number_} typed question{'s' if questions_number_ != 1 else ''} "
          f"at level {cefr_level_.name} in {vocabulary_.name.capitalize()} using "
          f"{file_names(vocabulary_, file_numbers_)}.")
    print()

    client_: Optional[Any] = None
    if not demo_:
        from src.openai_integration import get_openai_client
        client_ = get_openai_client()

    questions_ = construct_questions(client_, vocabulary_, cefr_level_, questions_number_, file_numbers_, demo_)
    counts_ = {verdict_: 0 for verdict_ in VERDICTS}
    elapsed_ = 0.0

    for index_, question_ in enumerate(questions_):
        __print_question(index_, len(questions_), vocabulary_, question_)
        shown_at_ = perf_counter()

        answer_ = ""
        while not answer_:
            answer_ = " ".join(input(f"Your {vocabulary_.name.capitalize()} answer ({QUIT} to quit): ").split())
        print()
        if answer_.lower() == QUIT:
            break
        elapsed_ += perf_counter() - shown_at_

        print(__style("Checking...", DIM))
        try:
            correction_ = correct_answer(client_, vocabulary_, question_, answer_, demo_)
        except (JSONDecodeError, KeyError, TypeError) as error_:
            print(f"The correction could not be read ({type(error_).__name__}: {error_}).")
            correction_ = {"verdict": "correct" if answer_ == question_.correct_answer else "wrong_word"}
        print()

        counts_[__print_correction(question_, answer_, correction_)] += 1

    answered_ = sum(counts_.values())
    if not questions_:
        print("No questions were generated.")
    elif answered_ == 0:
        print("No questions were answered.")
    else:
        print(__style("─" * __width(), DIM))
        print(__style(f"Score: {counts_['correct']}/{answered_} correct ({counts_['correct'] / answered_:.0%}); "
                      f"{counts_['wrong_form']} right word in the wrong form, {counts_['wrong_word']} incorrect",
                      BOLD))
        print(time_summary(elapsed_, answered_))
    print()


DEMO_HELP: str = "use placeholder questions and corrections instead of the API, and do not record practice history"


def __run(vocabulary_: Vocabulary, cefr_level_: CEFRLevel, questions_number_: int, file_numbers_: List[int],
          demo_: bool):
    try:
        run_typed_quiz(vocabulary_, cefr_level_, questions_number_, file_numbers_, demo_)
    except KeyboardInterrupt:
        print()
        print()
    finally:
        print("Goodbye!")


def revise(command_line_arguments_: List[str]):
    revise_parser_ = argparse.ArgumentParser(
        prog=f"{basename(sys.argv[0])} {REVISE_COMMAND}",
        description=f"Run a typed revision quiz of {REVISION_QUESTIONS_NUMBER} questions drawn from all vocabulary "
                    f"files of a language; type '{QUIT}' at an answer prompt to quit.")
    revise_parser_.add_argument("-L", "--language", dest="vocabulary", default=DEFAULT_VOCABULARY, type=vocabulary,
                                metavar="LANGUAGE",
                                help=f"{', '.join(LANGUAGE_CODES)} (default: {language_code(DEFAULT_VOCABULARY)})")
    revise_parser_.add_argument("-l", "--level", dest="cefr_level", default=DEFAULT_CEFR_LEVEL, type=cefr_level,
                                metavar="LEVEL", help=f"CEFR level (default: {DEFAULT_CEFR_LEVEL.name})")
    revise_parser_.add_argument("--demo", action="store_true", help=DEMO_HELP)
    arguments_ = revise_parser_.parse_args(command_line_arguments_)

    __run(arguments_.vocabulary, arguments_.cefr_level, REVISION_QUESTIONS_NUMBER,
          get_vocabulary_file_numbers(arguments_.vocabulary), arguments_.demo)


EXAMPLES: List[Tuple[str, str]] = [
    ("", f"{DEFAULT_NUMBER_OF_QUESTIONS} {DEFAULT_VOCABULARY.name.capitalize()} questions at "
         f"{DEFAULT_CEFR_LEVEL.name} from the latest two files"),
    ("10 -L FR --level C1", "10 French questions at C1 from the latest two files"),
    ("5 -f 2", "5 German questions from german-2.md"),
    (f"-f {ALL_FILES}", f"{DEFAULT_NUMBER_OF_QUESTIONS} German questions from all files"),
    (REVISE_COMMAND, f"{REVISION_QUESTIONS_NUMBER} German questions from all files"),
    (f"{REVISE_COMMAND} -L FR -l C1", f"{REVISION_QUESTIONS_NUMBER} French questions at C1 from all files"),
    ("--demo", "placeholder questions and corrections, without calling the API or recording history"),
]

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == REVISE_COMMAND:
        revise(sys.argv[2:])
        sys.exit(0)

    command_line_argument_parser_ = argparse.ArgumentParser(
        usage="%(prog)s [-h] [-L LANGUAGE] [-l LEVEL] [-f N] [--demo] [questions_number]\n"
              f"       %(prog)s {REVISE_COMMAND} [-h] [-L LANGUAGE] [-l LEVEL] [--demo]",
        description=fill("Typed vocabulary quiz. Like the multiple choice quiz, but the choices are shown "
                         "only in English: type the missing word yourself, in the form the sentence needs, and get "
                         f"a correction with comments and suggestions. Type '{QUIT}' to quit.", width=90),
        epilog="commands:\n"
               f"  {REVISE_COMMAND} [-L LANGUAGE] [-l LEVEL] [--demo]\n"
               f"      typed revision quiz of {REVISION_QUESTIONS_NUMBER} questions from all files; same -L, -l, and "
               "--demo as the quiz\n\n"
               "examples:\n" +
               "\n".join(f"  %(prog)s {example_:<{max(len(example_) for example_, _ in EXAMPLES)}}  {text_}"
                         for example_, text_ in EXAMPLES),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    command_line_argument_parser_.add_argument("questions_number", nargs="?", default=DEFAULT_NUMBER_OF_QUESTIONS,
                                               type=positive_integer,
                                               help=f"number of questions (default: {DEFAULT_NUMBER_OF_QUESTIONS})")
    command_line_argument_parser_.add_argument("-L", "--language", dest="vocabulary", default=DEFAULT_VOCABULARY,
                                               type=vocabulary, metavar="LANGUAGE",
                                               help=f"{', '.join(LANGUAGE_CODES)} "
                                                    f"(default: {language_code(DEFAULT_VOCABULARY)})")
    command_line_argument_parser_.add_argument("-l", "--level", dest="cefr_level", default=DEFAULT_CEFR_LEVEL,
                                               type=cefr_level, metavar="LEVEL",
                                               help=f"CEFR level (default: {DEFAULT_CEFR_LEVEL.name})")
    command_line_argument_parser_.add_argument("-f", "--file", dest="file_number", default=None,
                                               type=file_number_or_all, metavar="N",
                                               help=f"only use the vocabulary file <language>-N.md; '{LATEST_FILE}' "
                                                    f"for the latest {LATEST_FILES_NUMBER} files, i.e. the highest N "
                                                    f"and N - 1, or '{ALL_FILES}' for all files (default: "
                                                    f"{LATEST_FILE})")
    command_line_argument_parser_.add_argument("--demo", action="store_true", help=DEMO_HELP)
    arguments_ = command_line_argument_parser_.parse_args()
    file_numbers_ = resolve_file_numbers(command_line_argument_parser_, "-f/--file", arguments_.vocabulary,
                                         arguments_.file_number)

    __run(arguments_.vocabulary, arguments_.cefr_level, arguments_.questions_number, file_numbers_, arguments_.demo)
