**Disclaimer:** This file was generated entirely by OpenAI GPT-6. The original repository code was written without AI; the `cefr_level` parser and console argument were added with AI assistance.

# Languages

## Overview

**Languages** is a personal, noncommercial project for practising English, German, and French vocabulary. Markdown entries provide definitions, grammar, examples, and translations. Python uses the OpenAI API to generate contextual multiple choice exercises.

## Console Usage

Install the dependencies from `requirements.txt` and configure `OPENAI_API_KEY` in the repository's root `.env` file.

From the repository root, run `python3 run_console.py [vocabulary] [questions_number] [cefr_level]`. All three positional arguments are optional; square brackets indicate optional values and should not be typed.

Use `EN` for English, `DE` for German, or `FR` for French. The second argument is a positive question count. The third accepts `A1`, `A2`, `B1`, `B2`, `C1`, or `C2`. Language codes and levels are case insensitive. Arguments follow this order.

For example, `python3 run_console.py DE 10 C1` generates ten German questions at C1. `python3 run_console.py EN` uses English with the default count and level. Running `python3 run_console.py` currently selects four French questions at B2. Defaults are set in `src/configuration.py`.

Answer each question with its displayed letter. The console provides feedback, completed sentences, English translations, and a final percentage score.

## Selection and Interfaces

SQLite records previously selected terms. Weighted sampling favours unseen vocabulary and terms used less recently. The repository also includes a Flask API and an early React and TypeScript interface.
