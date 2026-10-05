**Disclaimer:** This README.md file was generated using OpenAI's GPT-6 Astra model. The repository's original
code was written without AI in its entirety. The definitions in the vocabulary files were generated using various AI
models.

# Languages

## Overview

Languages is a personal project for learning English, German, and French vocabulary. It reads Markdown
vocabulary collections and uses the OpenAI API (`gpt-6-sol`) to generate two kinds of exercises: contextual multiple
choice questions and free-form writing exercises. The console checks multiple choice answers, displays completed
sentences and English translations, and reports a percentage score.

## Console Usage

Install the dependencies from `requirements.txt` and set up an `OPENAI_API_KEY`. From the
repository root, run `python3 run.py [questions_number] [--language LANGUAGE] [--level LEVEL] [--file N]`.
All arguments are optional; omit the brackets. The question count must be a positive integer and defaults to four.
`--language` (`-L`) accepts `EN`, `DE`, or `FR` and defaults to `DE`. `--level` (`-l`) chooses the CEFR level among
`A1`, `A2`, `B1`, `B2`, `C1`, or `C2` and defaults to `B2`. `--file` (`-f`) chooses the file the questions come from,
e.g. `-f 2` draws only from `german-2.md`, `-f latest` uses the latest file, and `-f all` uses all of the language's
files; without it, only the latest
file (the one with the highest number) is used. Language codes and levels
are case-insensitive.

For example, `python3 run.py 10 -L FR --level C1` requests ten French multiple choice questions at C1, and
`python3 run.py 5 -f 2` requests five German questions at B2 drawn only from `german-2.md`. Running the
script without any arguments uses the defaults (four German questions at B2 from the latest German file), which are defined in
`src/configuration.py`; `python3 run.py --help` prints the usage.

## Anki Decks

`python3 run.py create_anki [LANGUAGE] [N]` converts vocabulary files into Anki decks under
`vocabulary/anki/<language>`. `LANGUAGE` is `EN`, `DE`, or `FR` (case-insensitive) and defaults to `DE`. With `N`,
only `<language>-N.md` is converted into `<language>-N-<date>.csv`; with `N` = `all`, all of the language's files are
combined into `<language>-all-<date>.csv`; with `N` = `latest` or without it, the latest file (the highest number) is
converted. Without any
arguments, `create_anki` therefore converts the latest German file. `<date>` is the day the deck was created (`YYYY-MM-DD`), so decks from earlier days are
kept, while a deck created again on the same day overwrites that day's file. For example, running
`python3 run.py create_anki DE 4` on 5 October 2026 creates `vocabulary/anki/german/german-4-2026-10-05.csv`.

Each `## ` heading becomes the front of a card. The back holds the Definition, Grammar, Example, Synonym,
English/French, and CEFR sections in that order, with Markdown converted to HTML. To import a deck, choose
comma-separated fields and enable "Allow HTML in fields". The conversion lives in `src/anki_deck/converter.py`.

## Vocabulary Info

`python3 run.py info [--language LANGUAGE]` reports how many vocabulary files a language has, the number of terms in
each file, and the total. `--language` (`-l`) accepts `EN`, `DE`, or `FR` and defaults to `DE`.

## Writing Exercise

The second exercise type is a free-form writing exercise, driven by `single_writing_exercise`
in `src/openai_integration.py`. Given a sample of vocabulary entries and a CEFR level, the model invents a subject
that incorporates those terms and poses it as a short question. The learner types a sentence or short paragraph in
response directly in the console. The model then grades the answer on a scale from 1 to 20 and returns comments on
grammar, syntax, spelling, and general appropriateness, an encouraging remark, a corrected version close to what the
learner wrote, and a fully correct version at the target CEFR level. Typing `quit` or submitting an empty answer skips
grading. This exercise is not wired into the CLI; try it with `python3 -m research.writing_exercise` from the repository
root (see `research/`).

## Sampling

Sampling favours unfamiliar vocabulary and revisits older material. Within the chosen language's history of n terms,
seen terms receive weights linearly from zero to n minus one,
newest first. Unseen terms receive `n + 1 + UNSEEN_ALPHA` where UNSEEN_ALPHA favours the unseen vocabulary.
