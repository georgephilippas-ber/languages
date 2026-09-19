from dataclasses import asdict
from json import dumps

from src.domain import Entry, CEFRLevel, Vocabulary


def single_multiple_choice_question_prompt(entry_: Entry, vocabulary_: Vocabulary, cefr_level_: CEFRLevel):
    dict_ = asdict(entry_)

    try:
        del dict_["example"]
    except KeyError:
        pass

    return f"""
Create exactly one {vocabulary_.name.lower()} fill-in-the-blank multiple-choice vocabulary question
at CEFR level {cefr_level_.value}.

The purpose of the question is to test whether the learner can correctly use
the vocabulary term in the supplied entry.

Vocabulary entry:
{dumps(asdict(entry_), ensure_ascii=False)}

Requirements:
- Write the question entirely in German.
- Create exactly one blank, written as _____.
- The sentence must be natural, idiomatic, and appropriate for CEFR level {cefr_level_.value}.
- Invent a new context. Do NOT copy or closely paraphrase the example from the entry.
- The intended answer must test the supplied term.
- You may use the grammatically required inflected, conjugated, or declined form
  of the term rather than its dictionary form.
- If the term is a fixed expression or construction, test the complete expression
  when this is more natural.
- Provide exactly 4 choices.
- Exactly one choice must be correct.
- The three incorrect choices must be plausible German distractors.
- Distractors should preferably have the same grammatical role as the correct answer.
- Avoid obviously absurd distractors.
- Make the distinction semantic or grammatical enough that only one answer is defensible.
- Do not include the answer anywhere in the question outside the choices.
- `correct_choice` is the zero-based index of the correct answer.
- Return only the requested structured result, with no explanation or commentary.

Output shape:
{{
    "question": "German sentence containing _____",
    "choices": ["choice 1", "choice 2", "choice 3", "choice 4"],
    "correct_choice": 0
}}
"""
