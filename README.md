**Disclaimer:** This README.md file was generated using OpenAI's GPT-6 Astra model. The repository's original
code was written without AI in its entirety. The definitions in the vocabulary files were generated using various AI
models.

# Languages

## Overview

Languages is a personal project for learning English, German, and French vocabulary. It reads Markdown
vocabulary collections and uses the OpenAI API (`gpt-6-sol`) to generate two kinds of exercises: contextual multiple
choice questions and free-form writing exercises. The console checks multiple choice answers, displays completed
sentences and English translations, and reports a percentage score.

## Console Usage

Install the dependencies from `requirements.txt` and set up an `OPENAI_API_KEY`. From the
repository root, run `python3 run_console.py [vocabulary] [questions_number] [cefr_level]`. All arguments are optional
and positional; omit the brackets. Vocabulary accepts `ENGLISH`, `GERMAN`, or `FRENCH`; the question count must be a
positive integer. CEFR can be chosen among `A1`, `A2`, `B1`, `B2`, `C1`, or `C2`. Names and levels are case-insensitive.

For example, `python3 run_console.py FRENCH 10 B2` requests ten French multiple choice questions at B2. Omitting all
arguments currently requests four German questions at C1. Defaults are defined in `src/configuration.py`.

## Writing Exercise

The second exercise type is a free-form writing exercise, driven by `single_writing_exercise`
in `src/openai_integration.py`. Given a sample of vocabulary entries and a CEFR level, the model invents a subject
that incorporates those terms and poses it as a short question. The learner types a sentence or short paragraph in
response directly in the console. The model then grades the answer on a scale from 1 to 20 and returns comments on
grammar, syntax, spelling, and general appropriateness, an encouraging remark, a corrected version close to what the
learner wrote, and a fully correct version at the target CEFR level. Typing `quit` or submitting an empty answer skips
grading. This exercise is currently only exercised through the `DEBUG` branch of `run_console.py` and is not yet wired
into the CLI's positional arguments.

## Sampling

Sampling favours unfamiliar vocabulary and revisits older material. Within the chosen language's history of n terms,
seen terms receive weights linearly from zero to n minus one,
newest first. Unseen terms receive `n + 1 + UNSEEN_ALPHA` where UNSEEN_ALPHA favours the unseen vocabulary.
