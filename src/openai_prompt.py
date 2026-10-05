from dataclasses import asdict
from json import dumps

from .domain import Entry, CEFRLevel, Vocabulary

from typing import List, Tuple


def __target_entry_dict(entry_: Entry) -> dict:
    # The example sentence is left out so that the model invents a new context; empty fields only cost tokens.
    return {key_: value_ for key_, value_ in asdict(entry_).items() if key_ != "example" and value_ is not None}


def multiple_choice_questions_prompt(entries_alternatives_: List[Tuple[Entry, List[str]]], vocabulary_: Vocabulary,
                                     cefr_level_: CEFRLevel) -> str:
    """One prompt for all questions of an exercise: the instructions are sent once, followed by one item per question
    (its target entry and the terms to use as incorrect choices). Items are numbered so that the questions in the
    response can be matched back to them."""
    items_ = [{"id": id_, "target_entry": __target_entry_dict(entry_), "incorrect_choice_terms": alternatives_}
              for id_, (entry_, alternatives_) in enumerate(entries_alternatives_, start=1)]

    return f"""
Create exactly {len(items_)} {vocabulary_.name.lower()} fill-in-the-blank multiple-choice
vocabulary questions at CEFR level {cefr_level_.name}, one for each item below.

The purpose of each question is to test whether the learner can correctly use
the vocabulary term in the item's target entry.

Items JSON (one question per item; "incorrect_choice_terms" are the vocabulary terms that
MUST be used as that question's incorrect answer choices):

{dumps(items_, ensure_ascii=False, indent=1)}

Requirements for every question:
- Write the question in [question] entirely in {vocabulary_.name.lower()}.
- Create exactly one blank within the question, written as _____.
- The sentence must be natural, idiomatic, and appropriate for CEFR level {cefr_level_.name}.
- Humour is allowed and encouraged.
- Each question must be sufficiently appropriate and complex for the selected CEFR level and must contain at least 10 words.
- Invent a new context, and use a different context or subject for each question.
- The intended correct answer must be the item's target vocabulary term.
- The other choices in [choices] must correspond exactly to the item's incorrect_choice_terms with changes to match only the missing word's part of speech.
- Do NOT invent additional distractor terms UNLESS the item's incorrect_choice_terms list is either EMPTY or contains fewer than three terms.
- All choices should be grammatically plausible in the blank whenever possible.
- Exactly one choice must be semantically and contextually correct.
- Make the distinction subtle enough to be useful at CEFR level {cefr_level_.name},
  but ensure that only one answer is defensible.
- Randomize the position of the correct answer among the four choices, independently for each question.
- Do not reveal the answer anywhere outside the choices.
- [correct_choice] must be the zero-based index of the correct answer.
- [english_translation] must contain ONLY the English translation of the complete sentence (the question correctly completed with the right missing word). Do NOT include translations of the choices in it.
- [choices_translations] must be a list with exactly one entry per choice, in the same order as [choices]: the short English meaning of that choice as it would read in the blank (e.g. "to advance", "tiny"), without numbering, letters, or commentary.
- Preferable subjects for the question sentences: everyday life, law, economics, finance.
- [complete_sentence] should be the original question sentence completed with the missing word in the appropriate form.
- [id] must be the id of the item the question was created for.

Return only the requested JSON object, with exactly one question per item in the order of the items,
and no explanation, commentary, or Markdown code fences.

Output shape:
{{
    "questions": [
        {{
            "id": int,
            "question": str,
            "choices": List[str],
            "choices_translations": List[str],
            "correct_choice": 0,
            "complete_sentence": str,
            "english_translation": str
        }}
    ]
}}"""
