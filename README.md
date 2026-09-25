**Disclaimer:** This README.md file was generated entirely using OpenAI's GPT-6 Astra model. The repository's original
code was written without AI in its entirety. The definitions in the vocabulary files were generated using various AI
models.

# Languages

## Overview

Languages is a personal project for learning English, German, and French vocabulary. It reads Markdown
vocabulary collections and uses the OpenAI API (`gpt-6-sol`) to generate contextual multiple choice exercises. The
console checks
answers, displays completed sentences and English translations, and reports a percentage score.

## Console Usage

Install the dependencies from `requirements.txt` and set `OPENAI_API_KEY` in the repository's `.env` file. From the
repository root, run `python3 run_console.py [vocabulary] [questions_number] [cefr_level]`. All arguments are optional
and positional; omit the brackets. Vocabulary accepts `ENGLISH`, `GERMAN`, or `FRENCH`; the question count must be a
positive integer. CEFR can be chosen among `A1`, `A2`, `B1`, `B2`, `C1`, or `C2`. Names and levels are case-insensitive.

For example, `python3 run_console.py FRENCH 10 B2` requests ten French questions at B2. Omitting all arguments currently
requests four German questions at C1. Defaults are defined in `src/configuration.py`.

## Sampling

Sampling favours unfamiliar vocabulary and revisits older material. Within the chosen language's history of n terms,
seen terms receive weights linearly from zero to n minus one,
newest first. Unseen terms receive `n + 1 + UNSEEN_ALPHA` where UNSEEN_ALPHA favours the unseen vocabulary.
