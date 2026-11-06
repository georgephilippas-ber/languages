**Disclaimer:** This README.md file was written with the help of Anthropic's Claude. The repository's original code
was written without AI in its entirety; later changes were made with the help of AI. The definitions in the vocabulary
files were generated using various AI models.

# Languages

Languages is a personal toolkit for building and practising English, German, and French vocabulary. Each term lives in
a plain Markdown file as a detailed entry, with a definition, grammar notes, example sentences, translations, and the
nuances that set it apart from similar words. From these files, three exercises use the OpenAI API to train every word
in three steps:

1. **Recognise** (multiple choice quiz): a fresh sentence at a chosen CEFR level, with one blank and four choices.
2. **Produce** (typed quiz): reveal a meaning hint if needed, then type the word yourself, in the form
   the sentence needs; the model then corrects your answer.
3. **Use** (writing exercise): you write your own sentence with two given words, and get a minimal fix of your errors,
   a version as a native speaker would say it, a translation, a check of each word, and a rating of how close your
   sentence is to a chosen CEFR level.

The quizzes favour the words you have not practised yet. All three exercises run in the browser as a web app, or in the
terminal as command-line scripts. The web app also fetches a current article to read (**Read**, always listed first),
writes new entries for you (**Add**), has flashcards with spaced repetition (**Review**), and answers questions about
language (**Ask**).
The web app also has **Connect**, a typed exercise for prepositions in all three languages, always beside **Use**, and
**Agree**, a typed exercise for the definite articles of the vocabulary's nouns, available in German and French;
both sit together in a header dropdown menu labelled **Refine**. **Translate** mixes all three languages in recognition and production exercises.

## Setup

Requires Python 3.10 or newer and an OpenAI API key. The web app also needs Node.js 20.19 or newer, once, to build its
frontend. From the repository root:

```bash
python3 -m pip install -r requirements.txt
mkdir -p ~/tmp/languages
echo "OPENAI_API_KEY=sk-..." > ~/tmp/languages/.env
cd frontend && npm install && npm run build && cd ..
```

The API key lives outside the repository. Instead of the `echo` line you can also set the key in the web app (see
below). The last line is only needed for the web app; run `npm run build` in `frontend/`
again whenever the frontend code changes.

## Web app

```bash
./scripts/run-dev.sh
```

`run-dev.sh` installs the frontend's packages if they are missing, rebuilds the frontend if its code has changed since the
last build, and then starts `./scripts/run_web.py`, passing on any of the options below (e.g. `./scripts/run-dev.sh --port 8080`). This
serves the app on http://127.0.0.1:8000 and opens it in the browser. The server listens on this computer only, and
the API key stays on the server: the browser never receives it.

To set or replace the API key, click the logo in the top-left corner and choose **API key**. A red dot on the logo
means no key is set. The key goes from the browser only to the local server (`PUT /api/settings/api-key`, accepted only
from this computer and the same origin). The server checks its format, writes it to `~/tmp/languages/.env` (readable
only by you, written atomically, other lines kept), and uses it from the next request on. Saving makes no network
request. Afterwards the app shows only the key's last four characters. Like any OpenAI client, the app then sends the
key to OpenAI, over HTTPS, only to authenticate its API calls.

| Option | Effect |
|---|---|
| `--port N` | another port (default 8000) |
| `--no-browser` | do not open the browser |
| `--reload` | restart the server when the Python code changes |
| `--host ADDRESS` | listen on another address, e.g. for a phone on your network, which can then use your API key |

The home page shows the exercises available for the selected language, which is switched at the top of every page (EN, DE,
FR). Each exercise starts with a setup panel for the CEFR level and number of questions or sentences. In Recognise,
Produce, and Use, choose a vocabulary category and then its last file, last two files, or entire category; choose
**All categories** to practise across all of them. The picker shows term counts and file numbers. Connect and Agree
retain their file selection controls.
The default level is C1; a previously chosen level is remembered. **Revise all** starts 20 questions from all files. The exercises work exactly as
on the command line, with the same prompts, defaults, practice history, and 40-second budget per quiz question, shown
here as a countdown ring. On top of that, the web app has:

- keyboard shortcuts: `1`–`4` or `A`–`D` to answer, `Enter` to start, check, and continue, `Esc` to end an exercise
- in the typed and prepositions quizzes, the answer is typed straight into the blank, with buttons for ä, ö, ü, ß (or the French accents)
- in Produce, the meaning hint is hidden until you reveal it; hints containing the answer or vocabulary term are withheld,
  and explicitly labelled hints are removed from the question sentence
- in Produce, **Reveal letter** can be used up to three times per question: the first press shows the first letter;
  later presses reveal every occurrence of a randomly chosen letter that is still hidden. Hint progress survives a reload
- **I give up** in the multiple choice, typed, and prepositions quizzes shows the answer without asking the model; the question
  counts as wrong
- feedback that highlights the exact letters or words that were corrected, and a **Listen** button that reads the
  sentence aloud with the browser's built-in voice
- a results page with the score, the breakdown, the time against the allotted time, and a review of every question
- an unfinished exercise survives a page reload and can be resumed later, as long as the language stays the same:
  switching the language discards every unfinished exercise and returns you to the home page
- light and dark themes, and a layout that works on a phone
- a model picker next to the theme button that lists up to eight OpenAI text models of GPT-5 and later that your API key
  can use (every model of the newest generation first, then the newest others, refreshed hourly, from `GET
  /api/models`); the choice is remembered in the browser and sent with every request in the `X-OpenAI-Model` header, and
  **default** marks `MODEL` from `src/configuration.py`, which the command line always uses

### Other devices

Open the logo menu and choose **Other devices**. **Local network** gives a QR code for devices on the same trusted
network; anyone on that network who knows the address can connect while sharing is enabled. The local connection uses
HTTP and is not encrypted. Revoke local access when finished.

**Internet via ngrok** works across networks. Install the ngrok agent and configure its account authtoken locally using
ngrok's setup instructions, then choose **Enable internet access**. Scan its QR code and enter the four-digit PIN shown on the Mac. Stop internet access to revoke the PIN and shut down the tunnel. The app's
settings and sharing controls remain available only on the Mac. ngrok provides the HTTPS connection; keep the Mac awake
and Languages running while using it. The same dialog offers keep-awake options from 30 minutes to three hours.

Vocabulary can be organised into **General**, **Legal**, and **Financial**, plus **Phrasal Verbs** for English. Choose a category in exercise and review
setup, or choose all files to practise across categories. Add remembers the selected category. Each category and
language has its own sequence of files, with a maximum of 25 entries per file. The 50 starter phrasal verbs progress
from everyday usage to advanced academic contexts; their CEFR estimates are approximate, not an official GRE list.

### Read

**Read** retrieves a real, dated article from a publisher feed before asking the model to summarize it.
Choose finance, law, physics, engineering, or politics and a CEFR level. English sources come from The Guardian,
German sources from tagesschau, and French sources from Le Monde or Sciences et Avenir. The server downloads the
article text and supplies it to the model as source data; the title, publication, link, and publication date come
from retrieval and cannot be replaced by the model. The summary has at most 80 words and highlights vocabulary
at the selected level. **Words to Add** sends those words to Add. Articles survive reloads per language.

Finance, law, and politics use articles published within 14 days; physics and engineering allow 90 days because
specialist feeds update less often. Dates appear on the article. Subscriber-only pages, unreadable pages, missing
dates, and stale items are skipped. If no suitable article is available, Read shows an error instead of inventing
coverage. Retrieval requires an internet connection; summaries still use your selected OpenAI model and API key.

### Mixed-language translation

**Translate** selects vocabulary from English, German, and French, independently of the header language. Each question
shows an original sentence and a translation in another language, with one or two vocabulary translations missing.
Choose **Recognize** for four possible answers or **Produce** to type the missing spans. Produce offers a meaning hint
and up to three letter reveals. English phrasal verbs are excluded by default; the setup checkbox includes them.
The selected model generates the questions and checks non-exact typed answers in context. As with other model-generated
feedback, an occasional ambiguous sentence or questionable correction is possible.

### Prepositions

**Connect** tests one missing preposition in a German, French, or English sentence. The vocabulary term stays visible,
and only the preposition is typed. For German and French, the full English translation stays hidden until you hover
over **English translation**, click or tap it, or activate the button with the keyboard. English questions offer a
**Meaning hint** instead, without the answer word. Clicking again hides the hint.

The exercise uses the same question count, CEFR level, file selection, **Revise all**, timing, and results as the
vocabulary quizzes. It selects terms with documented preposition patterns in their heading, grammar, or **Verb**
notes, using the same practice history and preference for unseen terms. Files without eligible terms produce a
message asking you to choose other files. German contractions are expanded so the answer is a single preposition.
French questions use complements that need no contraction or elision, keeping the sentence grammatical.

### Articles

**Agree** tests one missing definite article before a noun from the vocabulary, in German and French only; it sits with
**Connect** in the **Refine** dropdown menu in the header. The noun stays visible, and only the article is typed: der, die, das and
their case forms in German, le, la, les, or l’ in French. The full English translation stays hidden until you reveal it,
as in **Connect**.

The exercise uses the same question count, CEFR level, file selection, **Revise all**, timing, and results as the
vocabulary quizzes. It selects the terms whose heading starts with a definite article, using the same practice history
and preference for unseen terms. Files without eligible terms produce a message asking you to choose other files.
Asking for English is an error.

### Add

**Add** writes new entries. Type the words you met, one per line (optionally with a note after a dash on the sense you mean), and press **Write entries**. Each line
gets its own request to the model, which writes a full entry in the format of the existing files, using the latest
German entries as its model; up to three are written at a time. Every entry can be read in full, edited
as Markdown, or rewritten before **Add** appends it to the latest file of that language. A file holds at most
25 entries: the page shows where the next entry will go, and when a file is full, the next entry starts the next file.
After adding, the page lists each new term with its simplest English translation and the running count of the file.
Drafts survive a page reload. Duplicates are not checked.

**Translate** (⌥⌘T on a Mac, Ctrl+Alt+T elsewhere), above the text box, only translates the text in the box (from
the page's language into English, or from English into German on the English page; text in the other direction is
translated back) and adds a few succinct linguistic or grammar notes. It writes nothing and leaves the box as it is.

### Ask

**Ask** answers questions about language: grammar, meaning, usage, register, pronunciation, translation, etymology, or
how to learn a language. Questions are about the page's language unless they name another, and answers are in English.
Follow-up questions see the last six exchanges; the conversation survives a page reload, is kept per language, and
**Clear** removes it. The model is told to treat questions as data, not instructions, and declines anything that is not
about language, including attempts to change its rules. Nothing is written to the files.

### Review

**Review** turns the entries into flashcards, straight from the files.
Choose the files and the direction: the term on the front and its
meaning on the back, or the translation on the front and the term on the back. **Study** shows the cards that are
due, then up to 5, 10, 20, or 50 new cards. Reveal a card with `Space`, then grade it with `1`–`4` (again, hard,
good, easy); each button shows when the card will come back. Cards graded "again" come back 10 minutes later and
reappear at the end of the session; the others are scheduled days to months ahead, a little like Anki's SM-2
algorithm. The schedule is stored per language and direction in the table `flashcard_reviews` of
`vocabulary/history/history.db`. **Browse** shows all the cards of the selection, shuffled and without grading.

## Packaged app

```bash
./scripts/build.sh
open bin/Languages.app
```

The build needs Python, Node.js, and the Xcode Command Line Tools (`swiftc`). It bundles the Python runtime,
backend, compiled frontend, and native macOS launcher into `bin/Languages.app`. Move or copy that single app
bundle anywhere, including `/Applications`; it has no runtime dependency on this repository, Python, Node.js,
or Automator. The browser interface opens a shared tab in the existing Firefox instance at http://127.0.0.1:8100; no dedicated browser window or profile is created. Click its Dock icon to reopen the interface;
choose **Languages → Quit Languages** (⌘Q) to stop its server. You can also click the top-left Languages logo, choose **Exit** from its dropdown
and confirm **Quit**: the backend stops its server, the native app exits, and the page closes its own tab. Firefox
requires `dom.allow_scripts_to_close_windows=true` in `about:config` for ordinary tabs (configured on this Mac).
That preference allows other websites to close their own tabs too. If the browser blocks closing, the page says
that Languages has quit and can be closed manually. Startup errors appear in an alert and in
`~/tmp/languages/Languages.log`.

All runs use permanent storage at `~/tmp/languages`:

- `vocabulary/english/`, `vocabulary/french/`, `vocabulary/german/`: Markdown entries.
- `vocabulary/history/history.db`: practice history and flashcard schedules.
- `.env`: `OPENAI_API_KEY=...`, set by hand or from the logo menu's **API key** (an `OPENAI_API_KEY` environment
  variable set when launching takes precedence at launch, and the dialog says so).

Existing vocabulary and history were moved here from `bin/vocabulary`, including local changes. Both packaged
and development runs now share this data. Rebuilds never copy, reset, seed, or back it up. There is no second
development dataset and no automatic backup or standalone migration script. First launch on a new account creates empty
language directories and a history database; add entries through **Add**, or copy your vocabulary there.
The API key is external to the app bundle. On a new account, set it from the logo menu or create `~/tmp/languages/.env` before using AI features.
For isolated development or tests, set `LANGUAGES_DATA` to another directory.

`build.sh` maintains its build environment in `bin/.venv` and intermediate files in `bin/.build` and `bin/.dist`.
These are build artifacts; only `Languages.app` is needed to run. The bundle is signed locally for this Mac,
not notarized for public distribution.

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
| `-l`, `--level` | `A1`, `A2`, `B1`, `B2`, `C1`, `C2` | `C1` |
| `-f`, `--file` | a file number, `latest`, or `all` | `latest` |

`-f 2` draws questions only from `german-2.md`, `-f latest` from the two files with the highest numbers (e.g.
`german-5.md` and `german-6.md`, so that a new, still small file is practised together with the previous one), and
`-f all` from all of the language's files. `revise` runs 20 questions from all files, with the same `-L` and `-l`.

```bash
./scripts/console/run_vocabulary.py                      # 8 German questions at C1 from the latest two files
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
./scripts/console/run_typed_vocabulary.py [questions_number] [-L LANGUAGE] [-l LEVEL] [-f N]
./scripts/console/run_typed_vocabulary.py revise [-L LANGUAGE] [-l LEVEL]
```

The options and defaults are the same as in the multiple choice quiz, and the questions are chosen and generated the
same way, but without choices: you see only an English hint taken straight from the card (its English translation,
or its definition for English vocabulary), and you type the missing word yourself, in the form the sentence needs:
case, gender, number, ending, conjugation. Each answer is then sent back to the model with its question, which returns a verdict (correct, right
word in the wrong form, or wrong word), the corrected answer, every error with the rule behind it, a comment, and
suggestions. Type `q` to quit.

```bash
./scripts/console/run_typed_vocabulary.py              # 8 German questions at C1 from the latest two files
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
| `-l`, `--level` | `A1`, `A2`, `B1`, `B2`, `C1`, `C2` | `C1` |
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
The backend tests replace OpenAI with canned responses and run on a synthetic temporary vocabulary, so they need no
API key, cost nothing, and never touch your vocabulary files or practice history:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

`info` makes no API calls, so it is a quick way to check that the
vocabulary files still parse after a change. Defaults such as the number of questions, the level, and the time budget
are set in `src/configuration.py`.

### Additional regression checks

The default backend suite includes cross-process vocabulary saves, interrupted-write preservation, the transactional
upgrade from the old history key to `(vocabulary, term)`, file-number gaps, retrieved-source validation, and protected Exit.
The schema upgrade runs once when an old database is opened, preserving IDs, timestamps, and flashcard history.
Browser and bundle tests are opt-in and use disposable data, never your permanent vocabulary or paid model calls:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium firefox
./scripts/run-dev.sh --no-browser  # builds frontend/dist; stop it before the next commands
python3 -m pytest --run-browser tests/browser
./scripts/build.sh
python3 -m pytest --run-packaged tests/packaged
```

Browser checks cover Add/draft reload/save, exercise resumption and language switching, source dates and article
persistence, and Exit in Chromium and Firefox. Bundle checks copy the app to a new location and verify startup,
duplicate launches, native reopen, backend Exit, and shutdown. Close a running Languages instance before the native
check, which needs port 8100. `--app-path /path/to/Languages.app` selects a different built bundle.

## Project structure

```
bin/
  App.swift                native macOS launcher and server lifecycle
  launcher.py              bundled HTTP worker (port 8100)
  Languages.app/           complete movable application (generated)
scripts/
  run-dev.sh               builds the frontend if needed and starts the web app
  build.sh                 builds runtime and frontend, then the app bundle
  make-app.sh              assembles and signs the native app bundle
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
  articles.py              definite articles of nouns in German and French: eligible terms, questions, corrections
  article_sources.py       dated publisher feeds, bounded downloads, and article text extraction
  reading.py               grounded summaries, prompts, and the 80-word limit
  writing.py               writing exercise: word pairs, prompt, corrections
  adding.py                new entries: prompt, format checks, appending to the latest file
  flashcards.py            flashcards: cards from the files, spaced-repetition schedule
  library.py               reading and counting entries in the vocabulary files
  selection.py             choosing vocabulary files (latest, all, or one)
  launcher.py              the interactive console quiz
  parser.py                reading the vocabulary files
  database.py              practice history
  models.py                the OpenAI models offered in the web app
  history_schema.py        transactional history schema upgrade and composite key
  paths.py                 permanent data location and non-destructive initialization
  configuration.py         defaults
backend/
  app.py                   FastAPI app: the JSON API and the built frontend
  schemas.py               request and response models
frontend/                  React and TypeScript single-page app (Vite, Tailwind CSS)
  src/exercises/           one definition per exercise, run by a shared exercise runner
  src/components/          setup panel, runner, feedback, results, and shared UI
  src/pages/               home page, Read, Add, Review, and Ask
tests/                     backend tests (pytest, with OpenAI replaced by canned responses)
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
