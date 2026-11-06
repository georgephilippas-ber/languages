import json

import pytest

from src.domain import Entry
from src.typed import parse_questions_response, strip_question_hint


@pytest.mark.parametrize('question, expected', [
    ('After months without pruning, the balcony plants looked _____ rather than thick and healthy. (Hint: thin, uneven, and untidy in growth.)',
     'After months without pruning, the balcony plants looked _____ rather than thick and healthy.'),
    ('The plants looked _____ (Hint: thin (rather than dense)) after the summer.', 'The plants looked _____ after the summer.'),
    ('The plants looked _____. [HINT: uneven growth]', 'The plants looked _____.'),
    ('The plants looked _____. Hint: uneven growth', 'The plants looked _____.'),
    ('The plants looked _____.\nClue: uneven growth', 'The plants looked _____.'),
    ('Die Pflanzen wirkten _____. (Hinweis: unordentlich)', 'Die Pflanzen wirkten _____.'),
    ('Les plantes semblaient _____. [Indice : peu dense]', 'Les plantes semblaient _____.'),
    ('The plants (despite the rain) looked _____ and had uneven growth.', 'The plants (despite the rain) looked _____ and had uneven growth.'),
    ('A hint of rain made the plants look _____.', 'A hint of rain made the plants look _____.'),
])
def test_only_explicitly_labelled_hints_are_removed(question, expected):
    assert strip_question_hint(question) == expected


def test_parsed_question_and_completed_sentence_are_consistent():
    item = {'id': 1, 'question': 'The plants looked _____. (Hint: thin and untidy.)',
            'correct_answer': 'straggly', 'complete_sentence': 'The plants looked straggly. (Hint: thin and untidy.)',
            'english_translation': 'The plants looked straggly.'}
    question = parse_questions_response(json.dumps({'questions': [item]}),
                                        [Entry(term='straggly', definition='thin and untidy')])[0]
    assert question.question == 'The plants looked _____.'
    assert question.complete_sentence == 'The plants looked straggly.'


def test_prompt_separates_sentence_from_hints():
    from src.domain import CEFRLevel, Vocabulary
    from src.typed import questions_prompt
    prompt = questions_prompt([Entry(term='straggly')], Vocabulary.ENGLISH, CEFRLevel.C1)
    assert 'The app supplies any meaning hint separately' in prompt
    assert 'Do not add hints' in prompt
    assert 'concise, natural' in prompt and 'at least 10 words' not in prompt
    assert len(prompt.split()) < 180
