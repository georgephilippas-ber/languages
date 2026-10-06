**Disclaimer:** This README.md file was written with the help of Anthropic's Claude. The repository's original code
was written without AI in its entirety; later changes were made with the help of AI. The definitions in the vocabulary
files were generated using various AI models.

# Languages

Languages is a personal toolkit for building and practising English, German, and French vocabulary from the command
line. Each term lives in a plain Markdown file as a detailed entry, with a definition, grammar notes, example sentences,
translations, and the nuances that set it apart from similar words. From these files, the program uses the OpenAI API
to create fresh fill-in-the-blank quizzes at a chosen CEFR level, gives clear feedback with translations after every
answer, and favours the words you have not practised yet. A second exercise has you write your own sentences with
given terms and corrects and translates them. The same files can be exported as Anki decks for spaced repetition.

## Usage

### Setup

Requires Python 3.10 or newer and an OpenAI API key. From the repository root:

```bash
python3 -m pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env
```

The `.env` file is ignored by git. There are three executable scripts in `scripts/`: `run_vocabulary.py` for the
multiple choice quiz, revision, Anki decks, and vocabulary info, `run_writing.py` for the writing exercise, and
`run_typed_vocabulary.py` for the typed quiz. All of them can be started from any directory.

### Multiple choice quiz

```bash
./scripts/run_vocabulary.py [questions_number] [-L LANGUAGE] [-l LEVEL] [-f N]
```

| Option | Values | Default |
|---|---|---|
| `questions_number` | a positive integer | `8` |
| `-L`, `--language` | `EN`, `DE`, `FR` | `DE` |
| `-l`, `--level` | `A1`, `A2`, `B1`, `B2`, `C1`, `C2` | `B2` |
| `-f`, `--file` | a file number, `latest`, or `all` | `latest` |

Language codes, levels, and keywords are case-insensitive. `-f 2` draws questions only from `german-2.md`, `-f latest`
from the two files with the highest numbers (e.g. `german-5.md` and `german-6.md`, so that a new, still small file is
practised together with the previous one), and `-f all` from all of the language's files.

```bash
./scripts/run_vocabulary.py                      # 8 German questions at B2 from the latest two files
./scripts/run_vocabulary.py 10 -L FR --level C1  # 10 French questions at C1
./scripts/run_vocabulary.py 5 -f 2               # 5 German questions from german-2.md
./scripts/run_vocabulary.py -f all               # 8 German questions from all files
```

Answer each question with its letter. The feedback shows whether you were right, the completed sentence with its
English translation, and every choice with its own translation, marking the correct answer and yours. Each question
has a budget of 40 seconds, which is not enforced: the time from showing a question to your answer is added up, and
after the last question the score is shown together with your total time against the allotted time (40 seconds per
answered question) and how far under or over it you were. To stop early, type `q` at an answer prompt (the score and
time then cover the questions answered so far) or press Ctrl+C. Defaults, including `SECONDS_PER_QUESTION`, are set
in `src/configuration.py`.

### Revision quiz

```bash
./scripts/run_vocabulary.py revise [-L LANGUAGE] [-l LEVEL]
```

Runs the multiple choice quiz with 20 questions drawn from all of the language's files. `-L` and `-l` work as in the
quiz, with the same defaults (`DE` and `B2`).

```bash
./scripts/run_vocabulary.py revise               # 20 German questions at B2 from all files
./scripts/run_vocabulary.py revise -L FR -l C1   # 20 French questions at C1 from all files
```

### Anki decks

```bash
./scripts/run_vocabulary.py create_anki [LANGUAGE] [N]
```

Converts a vocabulary file into a CSV deck under `vocabulary/anki/<language>/`, named after the file and the current
date. `LANGUAGE` defaults to `DE` and `N` to `latest`; `N` = `all` combines all of the language's files into one deck.

```bash
./scripts/run_vocabulary.py create_anki          # latest German file -> german-<N>-<date>.csv
./scripts/run_vocabulary.py create_anki DE 4     # german-4.md        -> german-4-<date>.csv
./scripts/run_vocabulary.py create_anki FR all   # all French files   -> french-all-<date>.csv
```

Decks from earlier days are kept; creating the same deck again on the same day overwrites it. The command prints the
deck's file name and full path. Each entry's heading becomes the front of a card, and the back holds its Definition,
Grammar, Example, Synonym, English/French, and CEFR sections, formatted in HTML. To import a deck in Anki, choose
comma-separated fields and enable "Allow HTML in fields".

### Vocabulary info

```bash
./scripts/run_vocabulary.py info [-l LANGUAGE]
```

Lists a language's vocabulary files with the number of terms in each and in total. Note that here `-l` selects the
language (default `DE`).

### Writing exercise

```bash
./scripts/run_writing.py [questions_number] [-L LANGUAGE] [-f N]
```

| Option | Values | Default |
|---|---|---|
| `questions_number` | number of sentences, a positive integer | `4` |
| `-L`, `--language` | `EN`, `DE`, `FR` | `DE` |
| `-f`, `--file` | a file number, `latest`, or `all` | `latest` |

The options work as in the quiz: by default the words come from the latest two files, `-f 2` takes them from
`german-2.md`, and `-f all` from all of the language's files.

```bash
./scripts/run_writing.py            # 4 sentences in German, words from the latest two files
./scripts/run_writing.py 2 -L FR    # 2 sentences in French
./scripts/run_writing.py 6 -f all   # 6 sentences, words from all German files
```

Each round picks two terms from the chosen file or files and asks you to write one sentence that uses both; a short
meaning is shown next to each term. The model then returns two versions of your sentence: a minimal fix that
corrects only the actual errors and explains each one, and a natural version showing how a native speaker would say
it, with a short note on what makes it more idiomatic. It also translates the sentence and checks whether each term was
used correctly. Press Enter to skip a sentence, or type `quit` to stop.

### Typed quiz

```bash
./scripts/run_typed_vocabulary.py [questions_number] [-L LANGUAGE] [-l LEVEL] [-f N] [--demo]
./scripts/run_typed_vocabulary.py revise [-L LANGUAGE] [-l LEVEL] [--demo]
```

The options are the same as in the multiple choice quiz, with the same defaults. The questions are chosen and
generated the same way, but the four choices are shown only as their English meanings (German for English
vocabulary), and you type the missing word yourself, in the form the sentence needs: case, gender, number, ending,
conjugation. Each answer is then sent back to the model with its question, which returns a verdict (correct, right
word in the wrong form, or wrong word), the corrected answer, the errors with the rule behind each one, a comment, and
suggestions. Type `q` to quit. The 40-second budget and the time summary work as in the multiple choice quiz; the
time spent waiting for a correction does not count. `--demo` uses placeholder questions and a simple local check
instead of the API, and does not record practice history. `revise` works like the quiz's `revise`: 20 typed questions
from all files.

```bash
./scripts/run_typed_vocabulary.py              # 8 German questions at B2 from the latest two files
./scripts/run_typed_vocabulary.py 6 -l C1      # 6 German questions at C1
./scripts/run_typed_vocabulary.py -f all       # 8 German questions from all files
./scripts/run_typed_vocabulary.py revise       # 20 German questions from all files
```

Each script describes all of its options with `--help`, and `./scripts/run_vocabulary.py COMMAND --help` those of a
subcommand.

## How it works

**Vocabulary files.** Each language has numbered Markdown files in `vocabulary/<language>/` (`german-1.md`,
`german-2.md`, …). Every entry starts with a `## ` heading naming the term, followed by labelled sections: CEFR level,
Definition, Synonym, Grammar, Example, English and French translations, and an optional note on usage. New terms are
added to the latest file.

**Question generation.** All questions of a quiz are created with a single request to the OpenAI API, which keeps
token usage low. Each question tests one vocabulary term, and its incorrect choices are other terms from the quiz's
files; if they are too small, the missing choices come from the file before them. The response is checked before the
quiz starts, so an unusable question is skipped rather than shown.

**Choosing terms.** The program records when each term was last practised in `vocabulary/history/history.db` (SQLite)
and weights its choice accordingly. Within a language's history of n practised terms, weights rise linearly from 0 for
the most recently practised term to n − 1 for the least recent, while terms never practised receive n + 1 +
`UNSEEN_ALPHA` (set in `src/configuration.py`). New words therefore come up first, and older ones return over time.

## Project structure

```
scripts/
  run_vocabulary.py        multiple choice quiz, revise, create_anki, and info
  run_writing.py           sentence-writing exercise
  run_typed_vocabulary.py  typed quiz with corrections
src/
  openai_integration.py    question generation and term sampling
  openai_prompt.py         prompts sent to the OpenAI API
  launcher.py              the interactive console quiz
  parser.py                reading the vocabulary files
  database.py              practice history
  anki_deck/converter.py   Markdown to Anki CSV conversion
  configuration.py         defaults
vocabulary/
  english/  french/  german/   vocabulary files
  anki/                    generated Anki decks
  history/history.db       practice history
```
