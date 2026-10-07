# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Personal toolkit for practising English, German, and French vocabulary, as command-line scripts and as a local web
app. Vocabulary lives in numbered Markdown files; the exercises use the OpenAI API (Responses API, model `MODEL` in
`src/configuration.py`) to generate quizzes and correct answers.
`README.md` documents every command and option in detail.

## Commands

Setup: `python3 -m pip install -r requirements.txt`, with `OPENAI_API_KEY` in `.env` at the repo root (loaded via
`python-dotenv` in `src/openai_integration.py`).

```bash
./run.sh [options]                                                           # run_web.py, after npm install/build if needed
./scripts/run_web.py [--demo] [--host H] [--port N] [--no-browser] [--reload] # web app on http://127.0.0.1:8000
./scripts/run_vocabulary.py [N] [-L EN|DE|FR] [-l A1..C2] [-f N|latest|all]  # multiple choice quiz (8, DE, B2, latest)
./scripts/run_vocabulary.py revise [-L ..] [-l ..]                           # 20 questions from all files
./scripts/run_vocabulary.py info [-l LANG]                                   # term counts (here -l is the language)
./scripts/run_writing.py [N] [-L ..] [-f ..]                                 # sentence-writing exercise
./scripts/run_typed_vocabulary.py [N] [-L ..] [-l ..] [-f ..] [--demo]       # typed quiz with corrections
./scripts/run_typed_vocabulary.py revise [-L ..] [-l ..] [--demo]            # 20 typed questions from all files
```

In the exercises (quiz, writing, typed quiz) `latest` means the last two files. `--demo` (typed quiz, web app) runs
without the API and without writing practice history; the demo paths are `openai_construct_multiple_choice_questions`
(`demo=True`), and `construct_questions`, `check_answer`, and `check_sentence` (`demo_=True`).

Frontend (in `frontend/`, Node.js 20.19+): `npm install`, `npm run build` (type-checks with `tsc`, then builds
`frontend/dist`, which `run_web.py` serves), `npm run typecheck` (`tsc` only), `npm run dev` (Vite on :5173, proxying
`/api` to :8000). Backend tests: `python3 -m pip install -r requirements-dev.txt`, then `python3 -m pytest` (`tests/`,
demo mode; a fixture asserts that `history.db` is unchanged); one test with
`python3 -m pytest tests/test_api.py::test_typed_questions_and_checks`. There is no linter. `info`
makes no API calls, so it is the cheap way to check that parsing still works after a change. To check the web UI
without API cost, run `run_web.py --demo` and confirm `GET /api/meta` reports `"demo": true` before generating
anything.

## Architecture

- **Layers**: `src/` holds all exercise logic, shared by the CLI and the web app; `scripts/` holds only argparse
  and console output; `backend/` is a thin FastAPI layer over `src/`; `frontend/` is the browser UI. Change prompts,
  parsing, or corrections in `src/` only, so that both front ends stay identical.
- **Entry points** are the scripts in `scripts/` (argparse subcommands live in `run_vocabulary.py`, whose argument
  parsers/validators `run_writing.py` and `run_typed_vocabulary.py` import). Each script puts the repo root on
  `sys.path` before importing `src.*`; `src/` modules import each other as `src.*`. The scripts import each other
  directly, which works because Python puts the running script's directory (`scripts/`) on `sys.path` too.
- **Exercise modules**: `src/openai_integration.py` (multiple choice; also term sampling, `strip_code_fences`, and the
  lazily created OpenAI client `get_openai_client`), `src/typed.py` and `src/writing.py` (prompts, parsing, and
  `normalize_correction`, which turns the model's JSON into dataclasses; `check_answer`/`check_sentence` add the
  fallback for unreadable responses), `src/selection.py` (`select_file_numbers`, `describe_file_numbers`).
- **Add and Review** (web app only): `src/library.py` maps a `Kind` (vocabulary, idioms, grammatical) and language
  to its directory, for both `vocabulary/` and `expressions/`. `src/adding.py` writes one entry per request (the
  prompt shows the latest German entries of that kind as the format model), checks and re-wraps it at 120 columns
  (`normalize_entry`), and appends to the latest file, rolling over at `MAX_TERMS_PER_FILE` (25, in `src/library.py`)
  (`save_entries`; in demo mode it reports but writes nothing). `src/flashcards.py` reads cards straight from the
  files (`entry_sections`) and schedules them SM-2 style in the table `flashcard_reviews` of `history.db`, keyed by language, kind, term, and direction; the table is
  created on the first non-demo review.
- **Backend** (`backend/app.py`, `create_app(demo_)`): `GET /api/meta`; `GET /api/models` (`src/models.py`: the
  account's text models from `models.list()`, GPT-5 and later (`MIN_MODEL_GENERATION`), at most `MAX_MODELS` (8) with the whole newest generation first, filtered and cached for an hour, or `FALLBACK_MODELS` in demo mode or
  on failure); `POST /api/quiz`, `/api/typed`,
  `/api/writing` generate an exercise (`{language, level, count, files}`); `POST /api/typed/check` and
  `/api/writing/check` correct one answer; `POST /api/entries/define`, `/api/entries/save`, and
  `/api/entries/translate` (Add; translation only, in `src/translating.py`), `/api/flashcards` and
  `/api/flashcards/review` (Review), `/api/ask` (Ask; `src/asking.py`, language questions only: the rules go in the
  Responses API `instructions`, the question and history in `input`, and an off-topic reply is replaced server-side). Stateless: the browser sends back the question it needs checked. Every request may carry an
  `X-OpenAI-Model` header (an app-level async dependency validates it and sets the context variable that
  `current_model()` in `src/openai_integration.py` reads; every `responses.create` uses `current_model()`, falling back
  to `MODEL`, so the CLI is unchanged). JSON is camelCase
  via Pydantic aliases (`backend/schemas.py`); OpenAI failures become 502 with a readable `detail`. Unknown `/api/*`
  paths are a JSON 404; all other paths serve `frontend/dist` with an `index.html` fallback. Demo mode comes from `LANGUAGES_DEMO` when the app
  is created, so `run_web.py` runs `backend.app:create_app` as a factory after setting it; importing `backend.app`
  earlier builds `app` without demo mode.
- **Frontend** (React 19, TypeScript, Vite, Tailwind CSS v4, React Router, Motion, lucide-react): each exercise is an
  `ExerciseDefinition` in `src/exercises/` (generate, check, outcome, Question and Feedback views, review entry), all
  run by the generic `components/ExerciseRunner.tsx` (setup, loading, timer, progress, feedback, results, resume).
  Unfinished sessions and settings live in `localStorage` under `languages.*`. Changing the language discards all
  unfinished sessions (`setLanguage` in `context/MetaContext.tsx`), and the runner immediately restarts an exercise
  that is running or loading in the new language, with the same request; it never resumes across languages. Add,
  Review, and Ask are standalone pages in `src/pages/` (`AddPage.tsx`, `FlashcardsPage.tsx`, `AskPage.tsx`; not
  `ExerciseDefinition`s); Add
  keeps its drafts in `localStorage` and calls `refresh` in `MetaContext` after saving. The model picker (`components/ModelPicker.tsx`, next to the theme button) stores the choice under
  `languages.model` (`null` = default), and `api.ts` adds the header from it. Colours are CSS variables in `src/index.css` (light and `.dark`), exposed as Tailwind colours (`bg-surface`, `text-muted`,
  `text-good`, …).
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
- **Practice history**: SQLite at `vocabulary/history/history.db`, table `vocabulary_history` (term is UNIQUE, upserted
  with `last_trained_at`). It is committed to git, so it shows as modified after any quiz. Unseen terms get weight
  `n + 1 + UNSEEN_ALPHA` (`src/configuration.py`, which also holds the defaults).

## Adding vocabulary

- New terms go into the highest-numbered `<language>-N.md`. A file holds at most 25 terms (all languages).
- When a file reaches 25, the next term starts `<language>-(N+1).md`; if the latest file is already over 25, start
  the next file before adding.
- Don't create the next file until there is a term to put in it: "latest" is the highest-numbered file, so an empty
  file breaks the quiz.

## Expressions

- `expressions/idioms/<language>/<language>-<n>.md` holds fixed expressions and idioms;
  `expressions/grammatical/<language>/<language>-<n>.md` holds grammatical constructions (e.g. *Sollen … doch +
  Infinitiv!*). Same entry format and the same 25-terms-per-file rule as the vocabulary files.
- Only the web app's Add and Review pages read these directories (no quiz or `info`); don't change
  the other code for them unless asked.

## Conventions

- Python code style: local variables and parameters carry a trailing underscore (`entries_`, `vocabulary_`);
  module-private helpers use a double-underscore prefix. TypeScript uses standard camelCase.
- The code has no comments or docstrings (only the scripts' shebang lines), in Python and TypeScript; don't add any.
- In the frontend, don't pass a class to a component that conflicts with one of its own (e.g. `hidden` against
  `inline-flex`, `px-0` against `px-4`): Tailwind's order, not the class order, decides which wins. Wrap the element
  or add a prop instead.
- README.md states the original code was written without AI; keep README in sync when commands or options change.
