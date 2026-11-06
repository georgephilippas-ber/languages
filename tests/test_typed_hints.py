import json

import pytest

from src.domain import Entry
from src.typed import parse_questions_response


@pytest.mark.parametrize('term, answer, hint, expected', [
    ('die Katze', 'Katze', 'A small domestic feline', 'A small domestic feline'),
    ('die Katze', 'Katze', 'A Katze is a feline', ''),
    ('die Katze', 'Katzen', 'KATZE is the singular', ''),
    ('die Straße', 'Straßen', 'The STRASSE is a road', ''),
    ('to make up', 'makes up', 'She MAKES   UP a story', ''),
    ('l’été', 'été', "L'ETÉ is summer", ''),
    ('banana', 'BANANA', 'A yellow fruit', 'A yellow fruit'),
])
def test_generated_hint_does_not_contain_answer_or_headword(term, answer, hint, expected):
    entry = Entry(term=term, english=hint)
    body = {'questions': [{'id': 1, 'question': 'Here is _____.', 'correct_answer': answer,
                           'complete_sentence': f'Here is {answer}.', 'english_translation': 'A translation.'}]}
    question = parse_questions_response(json.dumps(body), [entry])[0]
    assert question.hint == expected


def test_safe_definition_is_used_when_translation_leaks_answer():
    entry = Entry(term='die Katze', english='Katze', definition='A small domestic feline')
    body = {'questions': [{'id': 1, 'question': 'Here is _____.', 'correct_answer': 'Katze',
                           'complete_sentence': 'Here is Katze.', 'english_translation': 'A translation.'}]}
    assert parse_questions_response(json.dumps(body), [entry])[0].hint == 'A small domestic feline'
