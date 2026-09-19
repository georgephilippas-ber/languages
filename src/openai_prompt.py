from dataclasses import asdict
from json import dumps

from .domain import Entry, CEFRLevel, Vocabulary
from typing import List


def single_multiple_choice_question_prompt(entry_: Entry, alternatives_: List[str], vocabulary_: Vocabulary, cefr_level_: CEFRLevel) -> str:
    dict_ = asdict(entry_)

    try:
        del dict_["example"]
    except KeyError:
        pass

    return f"""
Create exactly one {vocabulary_.name.lower()} fill-in-the-blank multiple-choice
vocabulary question at CEFR level {cefr_level_.name}.

The purpose of the question is to test whether the learner can correctly use
the vocabulary term in the supplied entry.

Target vocabulary entry:
{dumps(dict_, ensure_ascii=False)}

The following vocabulary terms MUST be used as the incorrect
answer choices:
{dumps(alternatives_, ensure_ascii=False)}

Requirements:
- Write the question entirely in {vocabulary_.name.lower()}.
- Create exactly one blank, written as _____.
- The sentence must be natural, idiomatic, and appropriate for CEFR level {cefr_level_.name}.
- Each question must be sufficiently appropriate and complex for the selected CEFR level and must contain at least 10 words.
- Invent a new context.
- The intended correct answer must be the target vocabulary term.
- The other three choices must correspond exactly to the three supplied alternative terms.
- Do NOT invent additional distractor terms UNLESS THE SUPPLIED LIST OF ALTERNATIVES IS either EMPTY or contains fewer than three terms.
- You may inflect, conjugate, decline, or otherwise grammatically adapt both the
  target term and the supplied alternatives when necessary for the sentence.
- Preserve the lexical identity and meaning of each supplied term when adapting it.
- If the target is a fixed expression or construction, test the complete expression
  when this is more natural.
- All choices should be grammatically plausible in the blank whenever possible.
- Exactly one choice must be semantically and contextually correct.
- Make the distinction subtle enough to be useful at CEFR level {cefr_level_.name},
  but ensure that only one answer is defensible.
- Avoid obviously absurd distractors.
- Randomize the position of the correct answer among the four choices.
- Do not reveal the answer anywhere outside the choices.
- `correct_choice` must be the zero-based index of the correct answer.
- Return only the requested structured result, with no explanation or commentary.

Output shape:
{{
    "question": str,
    "choices": List[str], 
    "correct_choice": 0
}}"""
