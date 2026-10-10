**Disclaimer:** This README.md file was written with the help of Anthropic's Claude. The repository's original code
was written without AI in its entirety; later changes were made with the help of AI. The definitions in the vocabulary
files were generated using various AI models.

# Languages

Languages is a personal toolkit for building and practising English, German, and French vocabulary. Each term lives in
a plain Markdown file as a detailed entry, with a definition, grammar notes, example sentences, translations, and the
nuances that set it apart from similar words. From these files, three exercises use the OpenAI API to train every word
in three steps:

1. **Recognise** (multiple choice quiz): a fresh sentence at a chosen CEFR level, with one blank and four choices.
2. **Produce** (typed quiz): only an English hint from the card is shown, and you type the word yourself, in the form
   the sentence needs; the model then corrects your answer.
3. **Use** (writing exercise): you write your own sentence with two given words, and get a minimal fix of your errors,
   a version as a native speaker would say it, a translation, a check of each word, and a rating of how close your
   sentence is to a chosen CEFR level.

The quizzes favour the words you have not practised yet. All three exercises run in the browser as a web app, or in the
terminal as command-line scripts. The web app also fetches a current article to read (**Read**, always listed first),
writes new entries for you (**Add**), has flashcards with spaced repetition (**Review**), and answers questions about
language (**Ask**).
The web app also has **Connect**, a typed exercise for prepositions in all three languages, always beside **Use**.

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
./scripts/run-dev.sh
```

`run-dev.sh` installs the frontend's packages if they are missing, rebuilds the frontend if its code has changed since the
last build, and then starts `./scripts/run_web.py`, passing on any of the options below (e.g. `./scripts/run-dev.sh --demo`). This
serves the app on http://127.0.0.1:8000 and opens it in the browser. The server listens on this computer only, and
the API key stays on the server: it never reaches the browser.

| Option | Effect |
|---|---|
| `--demo` | placeholder exercises and corrections, without calling the API or recording practice history |
| `--port N` | another port (default 8000) |
| `--no-browser` | do not open the browser |
| `--reload` | restart the server when the Python code changes |
| `--host ADDRESS` | listen on another address, e.g. for a phone on your network, which can then use your API key |

The home page shows the exercises available for the selected language, which is switched at the top of every page (EN, DE,
FR). Each exercise starts from the same setup panel: the CEFR level (for the quizzes), the number of questions or
sentences, and the files to draw words from (the latest two, the latest file, all files, or a single file, each with
its term count).
The last choices are remembered, and **Revise all** starts 20 questions from all files. The exercises work exactly as
on the command line, with the same prompts, defaults, practice history, and 40-second budget per quiz question, shown
here as a countdown ring. On top of that, the web app has:

- keyboard shortcuts: `1`–`4` or `A`–`D` to answer, `Enter` to start, check, and continue, `Esc` to end an exercise
- in the typed and prepositions quizzes, the answer is typed straight into the blank, with buttons for ä, ö, ü, ß (or the French accents)
- **I give up** in the multiple choice, typed, and prepositions quizzes shows the answer without asking the model; the question
  counts as wrong
- feedback that highlights the exact letters or words that were corrected, and a **Listen** button that reads the
  sentence aloud with the browser's built-in voice
- a results page with the score, the breakdown, the time against the allotted time, and a review of every question
- an unfinished exercise survives a page reload and can be resumed later, as long as the language stays the same:
  switching the language discards every unfinished exercise, and one in progress restarts at once in the new language,
  with the same settings, including in Connect
- light and dark themes, and a layout that works on a phone
- a model picker next to the theme button that lists up to eight OpenAI text models of GPT-5 and later that your API key
  can use (every model of the newest generation first, then the newest others, refreshed hourly, from `GET
  /api/models`); the choice is remembered in the browser and sent with every request in the `X-OpenAI-Model` header, and
  **default** marks `MODEL` from `src/configuration.py`, which the command line always uses

### Read

**Read** stands before the exercises everywhere in the app. It fetches a current article for reading practice: choose
one of the topics kept in the backend — finance, law, physics, engineering, or politics — and a CEFR level, then
press **Retrieve**. The model looks for a current article in the page's language and summarizes it in at most 80
words, written at the chosen level, which is picked before retrieving and shapes the summary; the words that carry
that level are highlighted in the summary. The model cannot browse, so the article is as current as its knowledge
allows; when it knows a link to the article, to the coverage it reports, or to a source that is cited, the link comes
with the summary and is attached to the publication — it is drawn from the model's memory, so check it before
trusting it. The article stays on the page and, per language, survives a reload: **Words to Add** puts the
highlighted words into the Add tab, and the exercises then practise them. In demo mode, the article is a
placeholder.

### Prepositions

**Connect** tests one missing preposition in a German, French, or English sentence. The vocabulary term stays visible,
and only the preposition is typed. For German and French, the full English translation stays hidden until you hover
over **English translation**, click or tap it, or activate the button with the keyboard. English questions offer a
**Meaning hint** instead, without the answer word. Clicking again hides the hint.

The exercise uses the same question count, CEFR level, file selection, **Revise all**, timing, and results as the
vocabulary quizzes. It selects terms with documented preposition patterns in their heading, grammar, or **Verb**
notes, using the same practice history and preference for unseen terms. Files without eligible terms produce a
message asking you to choose other files. In demo mode, questions use existing example sentences and translations
without API calls or history changes. German contractions are expanded so the answer is a single preposition.
French questions use complements that need no contraction or elision, keeping the sentence grammatical.

### Add

**Add** writes new entries. Type the words you met, one per line (optionally with a note after a dash on the sense you mean), and press **Write entries**. Each line
gets its own request to the model, which writes a full entry in the format of the existing files, using the latest
German entries as its model; up to three are written at a time. Every entry can be read in full, edited
as Markdown, or rewritten before **Add** appends it to the latest file of that language. A file holds at most
25 entries: the page shows where the next entry will go, and when a file is full, the next entry starts the next file.
After adding, the page lists each new term with its simplest English translation and the running count of the file.
Drafts survive a page reload. Duplicates are not checked. In demo mode, entries are
placeholders and nothing is written.

**Translate** (⌥⌘T on a Mac, Ctrl+Alt+T elsewhere), above the text box, only translates the text in the box (from
the page's language into English, or from English into German on the English page; text in the other direction is
translated back) and adds a few succinct linguistic or grammar notes. It writes nothing and leaves the box as it is.

### Ask

**Ask** answers questions about language: grammar, meaning, usage, register, pronunciation, translation, etymology, or
how to learn a language. Questions are about the page's language unless they name another, and answers are in English.
Follow-up questions see the last six exchanges; the conversation survives a page reload, is kept per language, and
**Clear** removes it. The model is told to treat questions as data, not instructions, and declines anything that is not
about language, including attempts to change its rules. Nothing is written to the files. In demo mode, answers are
placeholders.

### Review

**Review** turns the entries into flashcards, straight from the files.
Choose the files and the direction: the term on the front and its
meaning on the back, or the translation on the front and the term on the back. **Study** shows the cards that are
due, then up to 5, 10, 20, or 50 new cards. Reveal a card with `Space`, then grade it with `1`–`4` (again, hard,
good, easy); each button shows when the card will come back. Cards graded "again" come back 10 minutes later and
reappear at the end of the session; the others are scheduled days to months ahead, a little like Anki's SM-2
algorithm. The schedule is stored per language and direction in the table `flashcard_reviews` of
`vocabulary/history/history.db`. **Browse** shows all the cards of the selection, shuffled and without grading. In
demo mode, grades are not saved.

## Packaged app

```bash
./scripts/build.sh
bin/languages [--demo] [--port N] [--no-browser]
```

`build.sh` builds a standalone copy of the web app into `bin/` and exits. It sets up its own virtual environment in
`bin/.venv` with PyInstaller, builds the frontend into `bin/.build` (leaving `frontend/dist` alone), and packages the
backend and frontend into one executable, `bin/languages`. It only rebuilds when the code has changed. `bin/languages`
starts the app on http://127.0.0.1:8100 and opens the browser; it takes `--demo`, `--port N`, and `--no-browser`.

The packaged app keeps its own data next to the executable and never touches the development data:
`bin/vocabulary/<language>/<language>-1.md` holds 8 terms per language and `bin/vocabulary/history/history.db` the
practice history, and `bin/.env` holds the API key (copied from `.env` on the first build). Every run of `build.sh`
resets `bin/vocabulary/` to factory settings: the same 8 terms per language, copied from `bin/factory/`, and an empty
history. `bin/factory/` is chosen at random from the development vocabulary only when it is missing, so delete it to
choose new terms. Starting `bin/languages` keeps the terms added and history recorded in the packaged app until the
next build.
Because it runs on its own port, the browser also keeps its unfinished sessions and settings apart from those of
`run-dev.sh`. Both apps can run at the same time.

`scripts/migrate-data.sh {to-production,to-development}` overwrites the practice data (vocabulary files and history)
of one environment with the other's: `to-production` copies `vocabulary/` to `bin/vocabulary/`, `to-development`
the reverse. Stop both apps before migrating.

## Command line

Each exercise also has a script in `scripts/console/`, and `run_vocabulary.py` also provides vocabulary info.
The scripts can be started from any directory. Each one describes all of its options with `--help`, and
`./scripts/console/run_vocabulary.py COMMAND --help` those of a subcommand. Language codes, levels, and keywords are
case-insensitive.

### Multiple choice quiz

```bash
./scripts/console/run_vocabulary.py [questions_number] [-L LANGUAGE] [-l LEVEL] [-f N]
./scripts/console/run_vocabulary.py revise [-L LANGUAGE] [-l LEVEL]
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
./scripts/console/run_vocabulary.py                      # 8 German questions at B2 from the latest two files
./scripts/console/run_vocabulary.py 10 -L FR --level C1  # 10 French questions at C1
./scripts/console/run_vocabulary.py 5 -f 2               # 5 German questions from german-2.md
./scripts/console/run_vocabulary.py -f all               # 8 German questions from all files
./scripts/console/run_vocabulary.py revise -L FR -l C1   # 20 French questions at C1 from all files
```

Answer each question with its letter. The feedback shows whether you were right, the completed sentence with its
English translation, and every choice with its own translation, marking the correct answer and yours. After the last
question, the score is shown together with the time summary (see [Time budget](#time-budget)). To stop early, type `q`
at an answer prompt (the score and time then cover the questions answered so far) or press Ctrl+C.

### Typed quiz

```bash
./scripts/console/run_typed_vocabulary.py [questions_number] [-L LANGUAGE] [-l LEVEL] [-f N] [--demo]
./scripts/console/run_typed_vocabulary.py revise [-L LANGUAGE] [-l LEVEL] [--demo]
```

The options and defaults are the same as in the multiple choice quiz, and the questions are chosen and generated the
same way, but without choices: you see only an English hint taken straight from the card (its English translation,
or its definition for English vocabulary), and you type the missing word yourself, in the form the sentence needs:
case, gender, number, ending, conjugation. Each answer is then sent back to the model with its question, which returns a verdict (correct, right
word in the wrong form, or wrong word), the corrected answer, every error with the rule behind it, a comment, and
suggestions. Type `q` to quit. `--demo` uses placeholder questions and a simple local check instead of the API, and
does not record practice history.

```bash
./scripts/console/run_typed_vocabulary.py              # 8 German questions at B2 from the latest two files
./scripts/console/run_typed_vocabulary.py 6 -l C1      # 6 German questions at C1
./scripts/console/run_typed_vocabulary.py revise       # 20 German questions from all files
```

### Writing exercise

```bash
./scripts/console/run_writing.py [questions_number] [-L LANGUAGE] [-l LEVEL] [-f N]
```

| Option | Values | Default |
|---|---|---|
| `questions_number` | number of sentences, a positive integer | `4` |
| `-L`, `--language` | `EN`, `DE`, `FR` | `DE` |
| `-l`, `--level` | `A1`, `A2`, `B1`, `B2`, `C1`, `C2` | `B2` |
| `-f`, `--file` | a file number, `latest`, or `all` | `latest` |

```bash
./scripts/console/run_writing.py            # 4 sentences in German, words from the latest two files
./scripts/console/run_writing.py 2 -L FR    # 2 sentences in French
./scripts/console/run_writing.py -l C1      # 4 sentences, each rated against level C1
./scripts/console/run_writing.py 6 -f all   # 6 sentences, words from all German files
```

Each round picks two terms from the chosen files and asks you to write one sentence that uses both; a short meaning is
shown next to each term. The model then returns two versions of your sentence: a minimal fix that corrects only the
actual errors and explains each one, and a natural version showing how a native speaker would say it, with a short
note on what makes it more idiomatic. It also translates the sentence, checks whether each term was used correctly, and rates the CEFR level your sentence
shows (vocabulary range, structures, complexity, accuracy) against the chosen level, saying how many levels above or
below it is and what would bring it up to that level; the summary counts the sentences at or above the level.
Press Enter to skip a sentence, or type `quit` to stop. The writing exercise is not timed.

### Vocabulary info

```bash
./scripts/console/run_vocabulary.py info [-l LANGUAGE]
```

Lists a language's vocabulary files with the number of terms in each and in total. Note that here `-l` selects the
language (default `DE`).

## How it works

### Vocabulary files

Each language has numbered Markdown files in `vocabulary/<language>/` (`german-1.md`,
`german-2.md`, …). Every entry starts with a `## ` heading naming the term, followed by labelled sections: CEFR level,
Definition, Synonym, Grammar, Example, translations into the other two languages, and an optional note on usage. New
terms are added to the latest file; a file holds at most 25 terms, and when it is full, the next term starts a new file.

### Question generation

All questions of a quiz are created with a single request to the OpenAI API, which keeps
token usage low. Each question tests one vocabulary term; in the multiple choice quiz, its incorrect choices are other
terms from the quiz's files, and if they are too small, the missing choices come from the file before them. The response is checked before the
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
TypeScript single-page app, in which one exercise runner drives all exercises through the same setup, timing,
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
the typed quiz with `--demo`. `info` makes no API calls, so it is a quick way to check that the
vocabulary files still parse after a change. Defaults such as the number of questions, the level, and the time budget
are set in `src/configuration.py`.

## Project structure

```
bin/
  launcher.py              entry point of the packaged app (port 8100, data in bin/)
  seed.py                  resets the packaged app's data to bin/factory/ (8 terms per language) and empty history
  factory/                 the packaged app's factory vocabulary
scripts/
  run-dev.sh               builds the frontend if needed and starts the web app
  build.sh                 builds the packaged app in bin/
  run_web.py               the web app: API and frontend on one local server
  console/
    run_vocabulary.py        multiple choice quiz, revise, and info
    run_typed_vocabulary.py  typed quiz with corrections
    run_writing.py           sentence-writing exercise
src/
  openai_integration.py    multiple choice question generation, term sampling, the OpenAI client
  openai_prompt.py         multiple choice prompt
  typed.py                 typed quiz: prompts, questions, corrections
  prepositions.py          prepositions in all three languages: eligible terms, questions, corrections
  reading.py               current articles: topics, prompt, and the 80-word summary check
  writing.py               writing exercise: word pairs, prompt, corrections
  adding.py                new entries: prompt, format checks, appending to the latest file
  flashcards.py            flashcards: cards from the files, spaced-repetition schedule
  library.py               reading and counting entries in the vocabulary files
  selection.py             choosing vocabulary files (latest, all, or one)
  launcher.py              the interactive console quiz
  parser.py                reading the vocabulary files
  database.py              practice history
  models.py                the OpenAI models offered in the web app
  configuration.py         defaults
backend/
  app.py                   FastAPI app: the JSON API and the built frontend
  schemas.py               request and response models
frontend/                  React and TypeScript single-page app (Vite, Tailwind CSS)
  src/exercises/           one definition per exercise, run by a shared exercise runner
  src/components/          setup panel, runner, feedback, results, and shared UI
  src/pages/               home page, Read, Add, Review, and Ask
tests/                     backend tests (pytest, demo mode)
vocabulary/
  english/  french/  german/   vocabulary files
  history/history.db       practice history
requirements.txt           Python dependencies
requirements-dev.txt       Python dependencies plus pytest and httpx, for the tests
```

## Lines of code

Counted on 8 October 2026: non-blank lines in the Python, TypeScript, CSS, and HTML files tracked by git. The code has
no comments, so all of them are code. Not included are the vocabulary files, the documentation, the
JSON, INI, and requirements files, and generated files such as `package-lock.json`.

| Part | Language | Files | Lines |
|---|---|---:|---:|
| `src/` (exercise logic shared by both front ends) | Python | 20 | 1,847 |
| `scripts/` (command line and launchers) | Python | 4 | 606 |
| `backend/` (API) | Python | 3 | 463 |
| `tests/` | Python | 2 | 397 |
| `frontend/` (web app) | TypeScript | 52 | 4,777 |
| `frontend/` | CSS | 1 | 86 |
| `frontend/` | HTML | 1 | 21 |
| **Total** | | **83** | **8,197** |

By language, that is 3,313 lines of Python, 4,777 of TypeScript, 86 of CSS, and 21 of HTML; with blank lines, the
files have 9,547 lines in total. To recount the total:

```bash
git ls-files '*.py' '*.ts' '*.tsx' '*.css' '*.html' | xargs cat | grep -cv '^[[:space:]]*$'
```
