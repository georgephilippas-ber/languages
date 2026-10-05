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
`A1`, `A2`, `B1`, `B2`, `C1`, or `C2` and defaults to `B2`. `--file` (`-f`) restricts the questions to a single file,
e.g. `-f 4` draws only from `german-4.md`; without it, all of the language's files are used. Language codes and levels
are case-insensitive.

For example, `python3 run.py 10 -L FR --level C1` requests ten French multiple choice questions at C1, and
`python3 run.py 5 -f 4` requests five German questions at B2 drawn only from `german-4.md`. Running the
script without any arguments uses the defaults (four German questions at B2 from all files), which are defined in
`src/configuration.py`; `python3 run.py --help` prints the usage.

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
