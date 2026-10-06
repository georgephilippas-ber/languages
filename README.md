**Disclaimer:** This README.md file was written with the help of Anthropic's Claude. The repository's original code
was written without AI in its entirety; later changes were made with the help of AI. The definitions in the vocabulary
files were generated using various AI models.

# Languages

Languages is a personal toolkit for building and practising English, German, and French vocabulary. Each term lives in
a plain Markdown file as a detailed entry, with a definition, grammar notes, example sentences, translations, and the
nuances that set it apart from similar words. From these files, three exercises use the OpenAI API to train every word
in three steps:

1. **Recognise** (multiple choice quiz): a fresh sentence at a chosen CEFR level, with one blank and four choices.
2. **Produce** (typed quiz): the choices are shown only by their meaning, and you type the word yourself, in the form
   the sentence needs; the model then corrects your answer.
3. **Use** (writing exercise): you write your own sentence with two given words, and get a minimal fix of your errors,
   a version as a native speaker would say it, a translation, and a check of each word.

The quizzes favour the words you have not practised yet. All three exercises run in the browser as a web app, or in the
terminal as command-line scripts. The web app also writes new entries for you (**Add**) and has flashcards with spaced
repetition (**Review**); the vocabulary files can still be exported as Anki decks.

## Setup

Requires Python 3.10 or newer and an OpenAI API key. The web app also needs Node.js 20.19 or newer, once, to build its
frontend. From the repository root:

```bash
python3 -m pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env
cd frontend && npm install && npm run build && cd ..
```

The `.env` file is ignored by git. The last line is only needed for the web app; run `npm run build` in `frontend/`
again whenever the frontend code changes.

## Web app

```bash
./run.sh
```

`run.sh` installs the frontend's packages if they are missing, rebuilds the frontend if its code has changed since the
last build, and then starts `./scripts/run_web.py`, passing on any of the options below (e.g. `./run.sh --demo`). This
serves the app on http://127.0.0.1:8000 and opens it in the browser. The server listens on this computer only, and
the API key stays on the server: it never reaches the browser.

| Option | Effect |
|---|---|
| `--demo` | placeholder exercises and corrections, without calling the API or recording practice history |
| `--port N` | another port (default 8000) |
| `--no-browser` | do not open the browser |
| `--reload` | restart the server when the Python code changes |
| `--host ADDRESS` | listen on another address, e.g. for a phone on your network, which can then use your API key |

The home page shows the three exercises side by side, and the language is switched at the top of every page (EN, DE,
FR). Each exercise starts from the same setup panel: the CEFR level (for the quizzes), the number of questions or
sentences, and the files to draw words from (the latest two, all files, or a single file, each with its term count).
The last choices are remembered, and **Revise all** starts 20 questions from all files. The exercises work exactly as
on the command line, with the same prompts, defaults, practice history, and 40-second budget per quiz question, shown
here as a countdown ring. On top of that, the web app has:

- keyboard shortcuts: `1`–`4` or `A`–`D` to answer, `Enter` to start, check, and continue, `Esc` to end an exercise
- in the typed quiz, the answer is typed straight into the blank, with buttons for ä, ö, ü, ß (or the French accents)
- feedback that highlights the exact letters or words that were corrected, and a **Listen** button that reads the
  sentence aloud with the browser's built-in voice
- a results page with the score, the breakdown, the time against the allotted time, and a review of every question
- an unfinished exercise survives a page reload and can be resumed later, as long as the language stays the same:
  switching the language discards every unfinished exercise, and one in progress restarts at once in the new language,
  with the same settings
- light and dark themes, and a layout that works on a phone

### Add

**Add** writes new entries. Choose the kind (vocabulary, idioms, or grammatical constructions), type the words you
met, one per line (optionally with a note after a dash on the sense you mean), and press **Write entries**. Each line
gets its own request to the model, which writes a full entry in the format of the existing files, using the latest
German entries of that kind as its model; up to three are written at a time. Every entry can be read in full, edited
as Markdown, or rewritten before **Add** appends it to the latest file of that language and kind. A file holds at most
25 entries: the page shows where the next entry will go, and when a file is full, the next entry starts the next file.
After adding, the page lists each new term with its simplest English translation and the running count of the file.
Drafts survive a page reload. Duplicates are not checked, and no Anki deck is created. In demo mode, entries are
placeholders and nothing is written.

### Review

**Review** turns the entries into flashcards, straight from the files, so there is no deck to export or import.
Choose the deck (vocabulary, idioms, or constructions), the files, and the direction: the term on the front and its
meaning on the back, or the translation on the front and the term on the back. **Study** shows the cards that are
due, then up to 5, 10, 20, or 50 new cards. Reveal a card with `Space`, then grade it with `1`–`4` (again, hard,
good, easy); each button shows when the card will come back. Cards graded "again" come back 10 minutes later and
reappear at the end of the session; the others are scheduled days to months ahead, a little like Anki's SM-2
algorithm. The schedule is stored per language, kind, and direction in the table `flashcard_reviews` of
`vocabulary/history/history.db`. **Browse** shows all the cards of the selection, shuffled and without grading. In
demo mode, grades are not saved.

## Command line

Each exercise also has a script in `scripts/`, and `run_vocabulary.py` provides the Anki export and vocabulary info.
The scripts can be started from any directory. Each one describes all of its options with `--help`, and
`./scripts/run_vocabulary.py COMMAND --help` those of a subcommand. Language codes, levels, and keywords are
case-insensitive.

### Multiple choice quiz

```bash
./scripts/run_vocabulary.py [questions_number] [-L LANGUAGE] [-l LEVEL] [-f N]
./scripts/run_vocabulary.py revise [-L LANGUAGE] [-l LEVEL]
```

| Option | Values | Default |
|---|---|---|
| `questions_number` | a positive integer | `8` |
| `-L`, `--language` | `EN`, `DE`, `FR` | `DE` |
| `-l`, `--level` | `A1`, `A2`, `B1`, `B2`, `C1`, `C2` | `B2` |
| `-f`, `--file` | a file number, `latest`, or `all` | `latest` |

`-f 2` draws questions only from `german-2.md`, `-f latest` from the two files with the highest numbers (e.g.
`german-5.md` and `german-6.md`, so that a new, still small file is practised together with the previous one), and
`-f all` from all of the language's files. `revise` runs 20 questions from all files, with the same `-L` and `-l`.

```bash
./scripts/run_vocabulary.py                      # 8 German questions at B2 from the latest two files
./scripts/run_vocabulary.py 10 -L FR --level C1  # 10 French questions at C1
./scripts/run_vocabulary.py 5 -f 2               # 5 German questions from german-2.md
./scripts/run_vocabulary.py -f all               # 8 German questions from all files
./scripts/run_vocabulary.py revise -L FR -l C1   # 20 French questions at C1 from all files
```

Answer each question with its letter. The feedback shows whether you were right, the completed sentence with its
English translation, and every choice with its own translation, marking the correct answer and yours. After the last
question, the score is shown together with the time summary (see [Time budget](#time-budget)). To stop early, type `q`
at an answer prompt (the score and time then cover the questions answered so far) or press Ctrl+C.

### Typed quiz

```bash
./scripts/run_typed_vocabulary.py [questions_number] [-L LANGUAGE] [-l LEVEL] [-f N] [--demo]
./scripts/run_typed_vocabulary.py revise [-L LANGUAGE] [-l LEVEL] [--demo]
```

The options and defaults are the same as in the multiple choice quiz, and the questions are chosen and generated the
same way. The four choices, however, are shown only as their English meanings (French meanings for English
vocabulary), and you type the missing word yourself, in the form the sentence needs: case, gender, number, ending,
conjugation. Each answer is then sent back to the model with its question, which returns a verdict (correct, right
word in the wrong form, or wrong word), the corrected answer, every error with the rule behind it, a comment, and
suggestions. Type `q` to quit. `--demo` uses placeholder questions and a simple local check instead of the API, and
does not record practice history.

```bash
./scripts/run_typed_vocabulary.py              # 8 German questions at B2 from the latest two files
./scripts/run_typed_vocabulary.py 6 -l C1      # 6 German questions at C1
./scripts/run_typed_vocabulary.py revise       # 20 German questions from all files
```

### Writing exercise

```bash
./scripts/run_writing.py [questions_number] [-L LANGUAGE] [-f N]
```

| Option | Values | Default |
|---|---|---|
| `questions_number` | number of sentences, a positive integer | `4` |
| `-L`, `--language` | `EN`, `DE`, `FR` | `DE` |
| `-f`, `--file` | a file number, `latest`, or `all` | `latest` |

```bash
./scripts/run_writing.py            # 4 sentences in German, words from the latest two files
./scripts/run_writing.py 2 -L FR    # 2 sentences in French
./scripts/run_writing.py 6 -f all   # 6 sentences, words from all German files
```

Each round picks two terms from the chosen files and asks you to write one sentence that uses both; a short meaning is
shown next to each term. The model then returns two versions of your sentence: a minimal fix that corrects only the
actual errors and explains each one, and a natural version showing how a native speaker would say it, with a short
note on what makes it more idiomatic. It also translates the sentence and checks whether each term was used correctly.
Press Enter to skip a sentence, or type `quit` to stop. The writing exercise is not timed.

### Anki decks

```bash
./scripts/run_vocabulary.py create_anki [LANGUAGE] [N]
```

Converts a vocabulary file into a CSV deck under `vocabulary/anki/<language>/`, named after the file and the current
date. `LANGUAGE` defaults to `DE` and `N` to `latest` (here the single file with the highest number); `N` = `all`
combines all of the language's files into one deck.

```bash
./scripts/run_vocabulary.py create_anki          # latest German file -> german-<N>-<date>.csv
./scripts/run_vocabulary.py create_anki DE 4     # german-4.md        -> german-4-<date>.csv
./scripts/run_vocabulary.py create_anki FR all   # all French files   -> french-all-<date>.csv
```

Decks from earlier days are kept; creating the same deck again on the same day overwrites it. The command prints the
deck's file name and full path. Each entry's heading becomes the front of a card, and the back holds its Definition,
Grammar, Example, Synonym, translation, and CEFR sections, formatted in HTML. To import a deck in Anki, choose
comma-separated fields and enable "Allow HTML in fields".

### Vocabulary info

```bash
./scripts/run_vocabulary.py info [-l LANGUAGE]
```

Lists a language's vocabulary files with the number of terms in each and in total. Note that here `-l` selects the
language (default `DE`).

## Expressions

Besides single words, idioms and grammatical constructions are collected in `expressions/`, in the same entry format
and with the same 25 entries per file as the vocabulary files:

- `expressions/idioms/<language>/<language>-<n>.md`: fixed expressions and idioms, such as *über den Tellerrand
  hinausblicken*
- `expressions/grammatical/<language>/<language>-<n>.md`: grammatical constructions, such as *Sollen … doch +
  Infinitiv!*

The web app's **Add** and **Review** pages work with expressions too; the exercises, `info`, and `create_anki` read
only `vocabulary/` so far. Anki decks for expressions are made with the
same converter and saved under `expressions/anki/<kind>/<language>/`, but there is no command for them yet.

## How it works

### Vocabulary files

Each language has numbered Markdown files in `vocabulary/<language>/` (`german-1.md`,
`german-2.md`, …). Every entry starts with a `## ` heading naming the term, followed by labelled sections: CEFR level,
Definition, Synonym, Grammar, Example, translations into the other two languages, and an optional note on usage. New
terms are added to the latest file; a file holds at most 25 terms, and when it is full, its Anki deck is created and
the next term starts a new file.

### Question generation

All questions of a quiz are created with a single request to the OpenAI API, which keeps
token usage low. Each question tests one vocabulary term, and its incorrect choices are other terms from the quiz's
files; if they are too small, the missing choices come from the file before them. The response is checked before the
quiz starts, so an unusable question is skipped rather than shown.

### Corrections

In the typed quiz and the writing exercise, every answer is corrected with its own request, so you
get feedback right away. If a correction cannot be read, the typed quiz falls back to comparing your answer with the
expected one, and the writing exercise reports the error: the command line moves on to the next sentence, and the
web app offers to try again.

### Choosing terms

The program records when each term was last practised in `vocabulary/history/history.db` (SQLite)
and weights its choice accordingly. Within a language's history of n practised terms, weights rise linearly from 0 for
the most recently practised term to n − 1 for the least recent, while terms never practised receive n + 1 +
`UNSEEN_ALPHA` (set in `src/configuration.py`). New words therefore come up first, and older ones return over time. A
term counts as practised as soon as a quiz question is generated for it. The writing exercise picks its words at random
and does not change the history.

### Time budget

Each quiz question has a budget of 40 seconds (`SECONDS_PER_QUESTION` in `src/configuration.py`), which is not
enforced: the time from showing a question to submitting your answer is added up, without the time spent waiting for
a correction. At the end, the total is compared with the allotted time, 40 seconds per answered question, and the
summary shows how far under or over it you were.

### Architecture

The exercise logic lives in `src/` and is shared by the command-line scripts and the web app, so both use
the same prompts, corrections, and practice history. The backend in `backend/` is a small FastAPI application that
exposes this logic as a JSON API under `/api` and serves the built frontend. The frontend in `frontend/` is a React and
TypeScript single-page app, in which one exercise runner drives all three exercises through the same setup, timing,
feedback, and results. The backend keeps no state between requests: the browser holds the current exercise and sends
back what a correction needs.

## Development

Run the API with automatic restarts and the Vite dev server, which forwards `/api` to it:

```bash
./scripts/run_web.py --reload --no-browser   # API on http://127.0.0.1:8000
cd frontend && npm run dev                   # frontend on http://localhost:5173
```

`npm run typecheck` in `frontend/` checks the TypeScript code, and `npm run build` checks it and builds `frontend/dist`.
The backend tests run against the API in demo mode, so they need no API key and never touch the practice history:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

To try changes without API costs, start the web app with `--demo` (or set `LANGUAGES_DEMO=1` for the API server), and
the typed quiz with `--demo`. `info` and `create_anki` make no API calls, so they are a quick way to check that the
vocabulary files still parse after a change. Defaults such as the number of questions, the level, and the time budget
are set in `src/configuration.py`.

## Project structure

```
run.sh                     builds the frontend if needed and starts the web app
scripts/
  run_web.py               the web app: API and frontend on one local server
  run_vocabulary.py        multiple choice quiz, revise, create_anki, and info
  run_typed_vocabulary.py  typed quiz with corrections
  run_writing.py           sentence-writing exercise
src/
  openai_integration.py    multiple choice question generation, term sampling, the OpenAI client
  openai_prompt.py         multiple choice prompt
  typed.py                 typed quiz: prompts, questions, corrections
  writing.py               writing exercise: word pairs, prompt, corrections
  adding.py                new entries: prompt, format checks, appending to the latest file
  flashcards.py            flashcards: cards from the files, spaced-repetition schedule
  library.py               the vocabulary and expressions files of each kind
  selection.py             choosing vocabulary files (latest, all, or one)
  launcher.py              the interactive console quiz
  parser.py                reading the vocabulary files
  database.py              practice history
  anki_deck/converter.py   Markdown to Anki CSV conversion
  configuration.py         defaults
backend/
  app.py                   FastAPI app: the JSON API and the built frontend
  schemas.py               request and response models
frontend/                  React and TypeScript single-page app (Vite, Tailwind CSS)
  src/exercises/           one definition per exercise, run by a shared exercise runner
  src/components/          setup panel, runner, feedback, results, and shared UI
  src/pages/               home page, Add, and Review
tests/                     backend tests (pytest, demo mode)
vocabulary/
  english/  french/  german/   vocabulary files
  anki/                    generated Anki decks
  history/history.db       practice history
expressions/
  idioms/<language>/       idioms and fixed expressions
  grammatical/<language>/  grammatical constructions
requirements.txt           Python dependencies
requirements-dev.txt       Python dependencies plus pytest and httpx, for the tests
```

## Lines of code

Counted on 6 October 2026: non-blank lines in the Python, TypeScript, CSS, and HTML files tracked by git. The code has
no comments, so all of them are code. Not included are the vocabulary and expression files, the documentation, the
JSON, INI, and requirements files, and generated files such as `package-lock.json`.

| Part | Language | Files | Lines |
|---|---|---:|---:|
| `src/` (exercise logic shared by both front ends) | Python | 14 | 965 |
| `scripts/` (command line) | Python | 4 | 641 |
| `backend/` (API) | Python | 3 | 246 |
| `tests/` | Python | 1 | 100 |
| `frontend/` (web app) | TypeScript | 43 | 2,655 |
| `frontend/` | CSS | 1 | 80 |
| `frontend/` | HTML | 1 | 21 |
| **Total** | | **67** | **4,708** |

By language, that is 1,952 lines of Python, 2,655 of TypeScript, 80 of CSS, and 21 of HTML; with blank lines, the
files have 5,531 lines in total. To recount the total:

```bash
git ls-files '*.py' '*.ts' '*.tsx' '*.css' '*.html' | xargs cat | grep -cv '^[[:space:]]*$'
```
