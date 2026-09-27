from dataclasses import asdict
from json import dumps

from .domain import Entry, CEFRLevel, Vocabulary

from typing import List


def single_multiple_choice_question_prompt(entry_: Entry, alternatives_: List[str], vocabulary_: Vocabulary,
                                           cefr_level_: CEFRLevel) -> str:
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

Target vocabulary entry JSON: 

{dumps(dict_, ensure_ascii=False)}

The following vocabulary terms MUST be used as the incorrect
answer choices:
{dumps(alternatives_, ensure_ascii=False)}

Requirements:
- Write the question in [question] entirely in {vocabulary_.name.lower()}.
- Create exactly one blank within the question, written as _____.
- The sentence must be natural, idiomatic, and appropriate for CEFR level {cefr_level_.name}.
- Humour is allowed and encouraged.
- Each question must be sufficiently appropriate and complex for the selected CEFR level and must contain at least 10 words.
- Invent a new context.
- The intended correct answer must be the target vocabulary term.
- The other choices in [choices] must correspond exactly to the supplied alternative terms with changes to match only the missing word's part of speech.
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
- [correct_choice] must be the zero-based index of the correct answer.
- [english_translation] should contain the translation in english of your question sentence (correctly completed with the right missing word) followed by a list of the english translation of all the other choices in the same string (if applicable).
- Return only the requested structured result, with no explanation or commentary.
- Preferable subjects for the question sentences: law, economics, finance, civil engineering, architecture.
- [complete_sentence] should be the original question sentence completed with the missing word in the appropriate form.

Output shape:
{{
    "question": str,
    "choices": List[str], 
    "correct_choice": 0,
    "complete_sentence": str
    "english_translation": str
}}"""


def writing_question_prompt(entry_list_: List[Entry], cefr_level: CEFRLevel) -> str:
    return f"""
Purpose: Learn a foreign language 

Task:
- Using terms you will be provided with in the language you are going to be provided with, 
you are tasked to produce a general question in no more than 20 to 30 words.
- The answer to this question must be a sentence or a paragraph of up to 40 words which will later be sent to you for linguistic correction. 
- The theme of the question should be general in context, inventive and should adhere to the specified level which will be provided.
- The theme MUST allow for easy incorporation of the terms given to you and must be appropriate both in terms of vocabulary and content to the CEFR level given.
- I will be prepending the sentence: 'Write a sentence or a short paragraph about [question]' to your response so your response should fluidly complete this.
 
Data:
* terms : [{','.join([entry_.term for entry_ in entry_list_])}] 
* level : {cefr_level.name} 

Response:
{{
    question: str
}}
"""


def correct_writing_question_prompt(vocabulary_: Vocabulary, cefr_level: CEFRLevel, question: str, answer: str) -> str:
    return f"""
A student is given a question (subject) and he is supposed to reply with a short sentence relevant to that subject. This is meant to aid foreign language learning at a given CEFR level. 

Task:
- Given the question, correct the answer across the following dimensions.
    - Syntax
    - Grammar
    - Spelling
    - Appropriateness to the given CEFR level
- Write your comments across these dimensions in a friendly manner.
- Write general advice as well
- Score the reply on a scale from 1 to 20:
    1: completely inadequate
    10: needs improvement
    15: would pass the relevant official CEFR level exam  
    20: genuinely good across most dimensions
- Include an encouraging objective remark based

Data:
language: {vocabulary_.name}
CEFR level: {cefr_level.name}
Question : {question}
Student's answer: {answer}

Reply:
{{
    score: int
    syntax_comments: str
    grammar_comments: str
    spelling_comments: str
    general_comments: str #general advice
    encouraging_objective_remark: str
}}
"""
