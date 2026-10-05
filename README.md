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

The `.env` file is ignored by git. There are two executable scripts: `./run_vocabulary.py` for the multiple choice
quiz, revision, Anki decks, and vocabulary info, and `./run_writing.py` for the writing exercise. Both can be started
from any directory.

### Multiple choice quiz

```bash
./run_vocabulary.py [questions_number] [-L LANGUAGE] [-l LEVEL] [-f N]
```

| Option | Values | Default |
|---|---|---|
| `questions_number` | a positive integer | `4` |
| `-L`, `--language` | `EN`, `DE`, `FR` | `DE` |
| `-l`, `--level` | `A1`, `A2`, `B1`, `B2`, `C1`, `C2` | `B2` |
| `-f`, `--file` | a file number, `latest`, or `all` | `latest` |

Language codes, levels, and keywords are case-insensitive. `-f 2` draws questions only from `german-2.md`, `-f latest`
from the file with the highest number, and `-f all` from all of the language's files.

```bash
./run_vocabulary.py                      # 4 German questions at B2 from the latest file
./run_vocabulary.py 10 -L FR --level C1  # 10 French questions at C1
./run_vocabulary.py 5 -f 2               # 5 German questions from german-2.md
./run_vocabulary.py -f all               # 4 German questions from all files
```

Answer each question with its letter. The feedback shows whether you were right, the completed sentence with its
English translation, and every choice with its own translation, marking the correct answer and yours. A score follows
the last question. To stop early, type `q` at an answer prompt (the score then covers the questions answered so far)
or press Ctrl+C. Defaults are set in `src/configuration.py`.

### Revision quiz

```bash
./run_vocabulary.py revise [-L LANGUAGE] [-l LEVEL]
```

Runs the multiple choice quiz with 20 questions drawn from all of the language's files. `-L` and `-l` work as in the
quiz, with the same defaults (`DE` and `B2`).

```bash
./run_vocabulary.py revise               # 20 German questions at B2 from all files
./run_vocabulary.py revise -L FR -l C1   # 20 French questions at C1 from all files
```

### Anki decks

```bash
./run_vocabulary.py create_anki [LANGUAGE] [N]
```

Converts a vocabulary file into a CSV deck under `vocabulary/anki/<language>/`, named after the file and the current
date. `LANGUAGE` defaults to `DE` and `N` to `latest`; `N` = `all` combines all of the language's files into one deck.

```bash
./run_vocabulary.py create_anki          # latest German file -> german-<N>-<date>.csv
./run_vocabulary.py create_anki DE 4     # german-4.md        -> german-4-<date>.csv
./run_vocabulary.py create_anki FR all   # all French files   -> french-all-<date>.csv
```

Decks from earlier days are kept; creating the same deck again on the same day overwrites it. The command prints the
deck's file name and full path. Each entry's heading becomes the front of a card, and the back holds its Definition,
Grammar, Example, Synonym, English/French, and CEFR sections, formatted in HTML. To import a deck in Anki, choose
comma-separated fields and enable "Allow HTML in fields".

### Vocabulary info

```bash
./run_vocabulary.py info [-l LANGUAGE]
```

Lists a language's vocabulary files with the number of terms in each and in total. Note that here `-l` selects the
language (default `DE`).

### Writing exercise

```bash
./run_writing.py [questions_number] [-L LANGUAGE] [-f N]
```

| Option | Values | Default |
|---|---|---|
| `questions_number` | number of sentences, a positive integer | `4` |
| `-L`, `--language` | `EN`, `DE`, `FR` | `DE` |
| `-f`, `--file` | a file number, `latest`, or `all` | `latest` |

The options work as in the quiz: by default the words come from the latest file, `-f 2` takes them from
`german-2.md`, and `-f all` from all of the language's files.

```bash
./run_writing.py            # 4 sentences in German, words from the latest file
./run_writing.py 2 -L FR    # 2 sentences in French
./run_writing.py 6 -f all   # 6 sentences, words from all German files
```

Each round picks two terms from the chosen file or files and asks you to write one sentence that uses both; a short
meaning is shown next to each term. The model then returns two versions of your sentence: a minimal fix that
corrects only the actual errors and explains each one, and a natural version showing how a native speaker would say
it, with a short note on what makes it more idiomatic. It also translates the sentence and checks whether each term was
used correctly. Press Enter to skip a sentence, or type `quit` to stop.

`./run_vocabulary.py --help`, `./run_vocabulary.py COMMAND --help`, and `./run_writing.py --help` describe all options.

## How it works

**Vocabulary files.** Each language has numbered Markdown files in `vocabulary/<language>/` (`german-1.md`,
`german-2.md`, …). Every entry starts with a `## ` heading naming the term, followed by labelled sections: CEFR level,
Definition, Synonym, Grammar, Example, English and French translations, and an optional note on usage. New terms are
added to the latest file.

**Question generation.** All questions of a quiz are created with a single request to the OpenAI API, which keeps
token usage low. Each question tests one vocabulary term, and its incorrect choices are other terms from the same file;
if that file is too small, the missing choices come from the previous file. The response is checked before the quiz
starts, so an unusable question is skipped rather than shown.

**Choosing terms.** The program records when each term was last practised in `vocabulary/history/history.db` (SQLite)
and weights its choice accordingly. Within a language's history of n practised terms, weights rise linearly from 0 for
the most recently practised term to n − 1 for the least recent, while terms never practised receive n + 1 +
`UNSEEN_ALPHA` (set in `src/configuration.py`). New words therefore come up first, and older ones return over time.

## Project structure

```
run_vocabulary.py          multiple choice quiz, revise, create_anki, and info
run_writing.py             sentence-writing exercise
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
