# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Personal command-line toolkit for practising English, German, and French vocabulary. Vocabulary lives in numbered
Markdown files; the scripts use the OpenAI API (Responses API, model `gpt-6-sol`) to generate quizzes and correct
sentences, and can export the files as Anki CSV decks. `README.md` documents every command and option in detail.

## Commands

Setup: `python3 -m pip install -r requirements.txt`, with `OPENAI_API_KEY` in `.env` at the repo root (loaded via
`python-dotenv` in `src/openai_integration.py`).

```bash
./scripts/run_vocabulary.py [N] [-L EN|DE|FR] [-l A1..C2] [-f N|latest|all]  # multiple choice quiz (8, DE, B2, latest)
./scripts/run_vocabulary.py revise [-L ..] [-l ..]                           # 20 questions from all files
./scripts/run_vocabulary.py create_anki [LANG] [N|latest|all]                # CSV deck -> vocabulary/anki/<language>/
./scripts/run_vocabulary.py info [-l LANG]                                   # term counts (here -l is the language)
./scripts/run_writing.py [N] [-L ..] [-f ..]                                 # sentence-writing exercise
./scripts/run_typed_vocabulary.py [N] [-L ..] [-l ..] [-f ..] [--demo]       # typed quiz with corrections
./scripts/run_typed_vocabulary.py revise [-L ..] [-l ..] [--demo]            # 20 typed questions from all files
```

In the exercises (quiz, writing, typed quiz) `latest` means the last two files. `run_typed_vocabulary.py --demo`
runs without the API and without writing practice history.

There is no test suite, linter, or build step. `info` and `create_anki` make no API calls, so they are the cheap way
to check that parsing still works after a change. `openai_construct_multiple_choice_questions(..., demo=True)` returns
Faker-generated questions without calling the API.

## Architecture

- **Entry points** are the three scripts in `scripts/` (argparse subcommands live in `run_vocabulary.py`;
  `run_writing.py` and `run_typed_vocabulary.py` import their argument parsers/validators from `run_vocabulary.py`
  and contain their own prompts, model constant, and console output rather than going through `src/`; the typed quiz
  reuses the original quiz's sampling and history from `src/`). Each script puts the repo root on `sys.path` before
  importing `src.*`; `src/` modules import each other as `src.*`. The scripts import each other directly, which works
  because Python puts the running script's directory (`scripts/`) on `sys.path` too.
- **Vocabulary files**: `vocabulary/<language>/<language>-<n>.md`. `src/domain.py`'s `Vocabulary` enum maps each
  language to its directory. `parser.get_vocabulary_file_numbers` assumes files are numbered contiguously from 1 (it
  counts `.md` files), so the latest file = highest number = file count. In the quiz and writing exercise, `latest`
  (the default) means the last `LATEST_FILES_NUMBER` (2) files (`resolve_file_numbers` in `run_vocabulary.py`); for
  `create_anki` it is still the single latest file (`resolve_file_number`).
- **Entry format**: each term starts with `## <term>`, followed by bold-labelled lines (`**CEFR:**`,
  `**Definition:**`, `**Synonym:**`, `**Grammar:**`, `**Example:**`, optional "Another example:", a translation line
  into the other two languages — German entries `**English:** … · **French:** …`, English entries
  `**German:** … · **French:** …`, French entries `**English:** … · **German:** …`) and an optional
  "Useful nuance:" paragraph. Match the format of existing entries exactly (see `german-3.md` onwards). The parser
  splits the whole file on `##`, so `##` must not appear inside entry text; term counts use `^## `.
- **Quiz flow** (`src/openai_integration.py`): terms are sampled with weights from `src/research.py`, using practice
  history from `src/database.py`; distractors come from other terms in the selected files (falling back to the previous
  file); all questions are generated in one API call from the prompt in `src/openai_prompt.py`, returned as JSON,
  validated per question (bad ones are skipped, not fatal), then run by `src/launcher.py`.
- **Practice history**: SQLite at `vocabulary/history/history.db`, table `vocabulary_history` (term is UNIQUE, upserted
  with `last_trained_at`). It is committed to git, so it shows as modified after any quiz. Unseen terms get weight
  `n + 1 + UNSEEN_ALPHA` (`src/configuration.py`, which also holds the defaults).
- **Anki export** (`src/anki_deck/converter.py`): heading → card front; selected sections → HTML back; output
  `<language>-<n|all>-<YYYY-MM-DD>.csv`.

## Adding vocabulary

- New terms go into the highest-numbered `<language>-N.md`. A file holds at most 25 terms (all languages;
  `english-1.md` and `french-1.md` predate the rule and are over the limit).
- When a term brings the file to 25, run `./scripts/run_vocabulary.py create_anki <LANG> N` in the same step. The next
  term starts `<language>-(N+1).md`; if the latest file is already over 25, start the next file before adding.
- Don't create the next file until there is a term to put in it: "latest" is the highest-numbered file, so an empty
  file breaks the quiz.

## Expressions

- `expressions/idioms/<language>/<language>-<n>.md` holds fixed expressions and idioms;
  `expressions/grammatical/<language>/<language>-<n>.md` holds grammatical constructions (e.g. *Sollen … doch +
  Infinitiv!*). Same entry format and the same 25-terms-per-file rule as the vocabulary files.
- The code does not read these directories yet (no quiz, `info`, or `create_anki`); don't change the code for them
  unless asked. Build their Anki decks by reusing `vocabulary_text_to_cards` from `src/anki_deck/converter.py` in a
  one-off script, writing `expressions/anki/<kind>/<language>/<language>-<kind>-<n>-<YYYY-MM-DD>.csv` (QUOTE_ALL CSV,
  like `create_anki_deck`). Build a file's deck when it reaches 10 entries, and again when it is complete at 25.

## Conventions

- Code style: local variables and parameters carry a trailing underscore (`entries_`, `vocabulary_`); module-private
  helpers use a double-underscore prefix.
- The code has no comments or docstrings (only the scripts' shebang lines); don't add any.
- README.md states the original code was written without AI; keep README in sync when commands or options change.
