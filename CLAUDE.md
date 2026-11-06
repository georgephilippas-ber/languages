# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Personal toolkit for practising English, German, and French vocabulary, as command-line scripts and as a local web
app. Vocabulary lives in numbered Markdown files; the exercises use the OpenAI API (Responses API, model `MODEL` in
`src/configuration.py`) to generate quizzes and correct answers.
`README.md` documents every command and option in detail.

## Commands

Setup: `python3 -m pip install -r requirements.txt`, with `OPENAI_API_KEY` in `~/tmp/languages/.env` (loaded via
`python-dotenv` in `src/openai_integration.py`).

```bash
./scripts/run-dev.sh [options]                                                      # run_web.py, after npm install/build if needed
./scripts/build.sh                                                                  # builds the self-contained bin/Languages.app
./scripts/make-app.sh                                                               # assembles the native app using the built runtime
./scripts/run_web.py [--host H] [--port N] [--no-browser] [--reload]                # web app on http://127.0.0.1:8000
./scripts/console/run_vocabulary.py [N] [-L EN|DE|FR] [-l A1..C2] [-f N|latest|all] # multiple choice quiz (8, DE, C1, latest)
./scripts/console/run_vocabulary.py revise [-L ..] [-l ..]                          # 20 questions from all files
./scripts/console/run_vocabulary.py info [-l LANG]                                  # term counts (here -l is the language)
./scripts/console/run_writing.py [N] [-L ..] [-f ..]                                # sentence-writing exercise
./scripts/console/run_typed_vocabulary.py [N] [-L ..] [-l ..] [-f ..]               # typed quiz with corrections
./scripts/console/run_typed_vocabulary.py revise [-L ..] [-l ..]                    # 20 typed questions from all files
```

In the exercises (quiz, writing, typed quiz) `latest` means the last two files. There is no demo mode: every
exercise calls the API.

Frontend (in `frontend/`, Node.js 20.19+): `npm install`, `npm run build` (type-checks with `tsc`, then builds
`frontend/dist`, which `run_web.py` serves), `npm run typecheck` (`tsc` only), `npm run dev` (Vite on :5173, proxying
`/api` to :8000). Backend tests: `python3 -m pip install -r requirements-dev.txt`, then `python3 -m pytest` (`tests/`;
`tests/conftest.py` points `LANGUAGES_DATA` at synthetic temporary vocabulary before `src` is imported, resets it
after every test, replaces `get_openai_client` in every `src` module with the `fake_openai` fixture, whose `reply()`
sets the canned response, and removes the temporary dataset at the end); one test with
`python3 -m pytest tests/test_api.py::test_typed_questions_and_checks`. There is no linter. `info`
makes no API calls, so it is the cheap way to check that parsing still works after a change. Running the web app
always calls the API, at the selected model's cost.

## Architecture

- **Layers**: `src/` holds all exercise logic, shared by the CLI and the web app; `scripts/` holds only argparse
  and console output; `backend/` is a thin FastAPI layer over `src/`; `frontend/` is the browser UI. Change prompts,
  parsing, or corrections in `src/` only, so that both front ends stay identical.
- **Entry points** are the scripts in `scripts/`: `run-dev.sh`, `build.sh`, and `run_web.py` (both `.sh` scripts
  `cd` to the repo root first), and the console exercises in `scripts/console/` (argparse subcommands live in
  `run_vocabulary.py`, whose argument parsers/validators `run_writing.py` and `run_typed_vocabulary.py` import). Each
  Python script puts the repo root on `sys.path` before importing `src.*`; `src/` modules import each other as `src.*`.
  The console scripts import each other directly, which works because Python puts the running script's directory
  (`scripts/console/`) on `sys.path` too.
- **Add and Review** (web app only): `src/library.py` reads and counts the entries of a language's files in
  `vocabulary/`. `src/adding.py` writes one entry per request (the prompt shows the latest German entries as the
  format model), checks and re-wraps it at 120 columns
  (`normalize_entry`), and appends to the latest file, rolling over at `MAX_TERMS_PER_FILE` (25, in `src/library.py`)
  (`save_entries`). `src/flashcards.py` reads cards straight from the
  files (`entry_sections`) and schedules them SM-2 style in the table `flashcard_reviews` of `history.db`, keyed by language, term, and direction; the table is
  created on the first review.
- **Backend** (`backend/app.py`, `create_app()`): `GET /api/meta`; `GET`/`PUT /api/settings/api-key` (`src/api_key.py`: status with the last four characters, or save the key to `DATA_ROOT/.env` atomically and reset the cached client and models; local same-origin requests only, no network call); `GET /api/models` (`src/models.py`: the
  account's text models from `models.list()`, GPT-5 and later (`MIN_MODEL_GENERATION`), at most `MAX_MODELS` (8) with the whole newest generation first, filtered and cached for an hour, or `FALLBACK_MODELS`
  on failure); `POST /api/quiz`, `/api/typed`,
  `/api/writing` generate an exercise (`{language, level, count, files}`); `POST /api/typed/check` and
  `/api/writing/check` correct one answer; `POST /api/prepositions`, `/api/prepositions/check`
  (`src/prepositions.py`, all three languages) and `POST /api/articles`, `/api/articles/check`
  (`src/articles.py`, German and French only) work like the typed quiz but test one missing preposition or
  definite article; `POST /api/entries/define`, `/api/entries/save`, and
  `/api/entries/translate` (Add; translation only, in `src/translating.py`), `/api/flashcards` and
  `/api/flashcards/review` (Review), `/api/ask` (Ask; `src/asking.py`, language questions only: the rules go in the
  Responses API `instructions`, the question and history in `input`, and an off-topic reply is replaced server-side). Stateless: the browser sends back the question it needs checked. Every request may carry an
  `X-OpenAI-Model` header (an app-level async dependency validates it and sets the context variable that
  `current_model()` in `src/openai_integration.py` reads; every `responses.create` uses `current_model()`, falling back
  to `MODEL`, so the CLI is unchanged). JSON is camelCase
  via Pydantic aliases (`backend/schemas.py`); OpenAI failures become 502 with a readable `detail`. Unknown `/api/*`
  paths are a JSON 404; all other paths serve `frontend/dist` with an `index.html` fallback. `run_web.py` runs
  `backend.app:create_app` as a factory.
- **Packaged app** (`scripts/build.sh`, `scripts/make-app.sh`, `bin/`): PyInstaller bundles the Python worker,
  backend, and compiled frontend. A native Cocoa launcher (`bin/App.swift`) manages the worker, browser reopening,
  and Quit. Everything required at runtime is inside `bin/Languages.app`; the bundle can move anywhere.
  All runs default to `~/tmp/languages` via `src/paths.py`, with an optional `LANGUAGES_DATA` override.
  Vocabulary and history are external to the bundle; initialization only creates missing directories and tables.
  No development dataset, seeding, or automatic backup scripts remain. History key upgrades run transactionally inside storage initialization. Tests generate synthetic temporary data.

- **Vocabulary files**: `vocabulary/<language>/<language>-<n>.md`. `src/domain.py`'s `Vocabulary` enum maps each
  language to its directory. `parser.get_vocabulary_file_numbers` assumes files are numbered contiguously from 1 (it
  counts `.md` files), so the latest file = highest number = file count. In the quiz and writing exercise, `latest`
  (the default) means the last `LATEST_FILES_NUMBER` (2) files (`select_file_numbers` in `src/selection.py`).
- **Entry format**: each term starts with `## <term>`, followed by bold-labelled lines (`**CEFR:**`,
  `**Definition:**`, `**Synonym:**`, `**Grammar:**`, `**Example:**`, optional "Another example:", a translation line
  into the other two languages — German entries `**English:** … · **French:** …`, English entries
  `**German:** … · **French:** …`, French entries `**English:** … · **German:** …`) and an optional
  "Useful nuance:" paragraph. Match the format of existing entries exactly (see `german-10.md` from `## die Ausgewogenheit` onwards). The parser
  splits the whole file on `##`, so `##` must not appear inside entry text; term counts use `^## `.
- **Quiz flow** (`src/openai_integration.py`): terms are sampled with weights from `src/research.py`, using practice
  history from `src/database.py`; distractors come from other terms in the selected files (falling back to the previous
  file); all questions are generated in one API call from the prompt in `src/openai_prompt.py`, returned as JSON,
  validated per question (bad ones are skipped, not fatal), then run by `src/launcher.py`.
- **Practice history**: SQLite at `vocabulary/history/history.db`, table `vocabulary_history` (`(vocabulary, term)` is UNIQUE, upserted
  with `last_trained_at`). It is committed to git, so it shows as modified after any quiz. Unseen terms get weight
  `n + 1 + UNSEEN_ALPHA` (`src/configuration.py`, which also holds the defaults).

## Adding vocabulary

- New terms go into the highest-numbered `<language>-N.md`. A file holds at most 25 terms (all languages).
- When a file reaches 25, the next term starts `<language>-(N+1).md`; if the latest file is already over 25, start
  the next file before adding.
- Don't create the next file until there is a term to put in it: "latest" is the highest-numbered file, so an empty
  file breaks the quiz.

## Conventions

- Python code style: local variables and parameters carry a trailing underscore (`entries_`, `vocabulary_`);
  module-private helpers use a double-underscore prefix. TypeScript uses standard camelCase.
- The code has no comments or docstrings (only the scripts' shebang lines), in Python and TypeScript; don't add any.
- README.md states the original code was written without AI; keep README in sync when commands or options change.

## Persistence and regression checks

Vocabulary saves in `src/adding.py` hold a process/thread lock for selection and rollover, fsync a temporary file,
and replace each destination atomically. Both file readers discover actual positive numbered language-N.md files;
quiz alternative sampling also uses actual existing file numbers. History uses UNIQUE(vocabulary, term);
`src/history_schema.py` upgrades old term-only keys transactionally, preserving rows and timestamps.

Read retrieves article text and feed metadata in `src/article_sources.py` before invoking the model. Metadata is
server-owned, including publishedAt/retrievedAt. Retrieval failures must not fall back to fabricated articles.
Exit uses a same-origin, per-server token and a delayed shutdown callback; native app exit follows worker exit.

Opt-in checks: `python3 -m pytest --run-browser tests/browser` (install Playwright browsers first), and
`python3 -m pytest --run-packaged tests/packaged` after building. All use temporary synthetic storage.
