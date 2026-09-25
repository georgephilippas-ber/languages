**Disclaimer:** This README was generated entirely by OpenAI GPT-6. The repository's original code was written without AI. The CEFR parser and console argument were subsequently added with AI assistance.

# Languages

## Overview

Languages is a personal, noncommercial project for practising English, German, and French vocabulary. It reads Markdown vocabulary collections and uses the OpenAI API to generate contextual multiple choice exercises. The console checks answers, displays completed sentences and English translations, and reports a percentage score.

## Console Usage

Install the dependencies from `requirements.txt` and set `OPENAI_API_KEY` in the repository's `.env` file. From the repository root, run `python3 run_console.py [vocabulary] [questions_number] [cefr_level]`. All arguments are optional and positional; omit the brackets. Vocabulary accepts `ENGLISH`, `GERMAN`, or `FRENCH`; the question count must be a positive integer. CEFR accepts `A1`, `A2`, `B1`, `B2`, `C1`, or `C2`. Names and levels are case insensitive.

For example, `python3 run_console.py FRENCH 10 B2` requests ten French questions at B2. Omitting all arguments currently requests four German questions at C1. Defaults are defined in `src/configuration.py`.

## Sampling

Sampling favours unfamiliar vocabulary and revisits older material. SQLite records each term's latest selection in a local database. Within the chosen language's history of n terms, seen terms receive weights from zero to n minus one, newest first. Unseen terms receive `n+1+UNSEEN_ALPHA`, with `UNSEEN_ALPHA` currently set to 30. Weights are divided by their sum to obtain probabilities. NumPy samples with replacement, allowing repeated terms within an exercise.
