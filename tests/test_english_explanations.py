from json import dumps
from src.domain import CEFRLevel, Entry, Vocabulary
from src.openai_prompt import multiple_choice_questions_prompt
from src.typed import questions_prompt
from src.prepositions import PrepositionEntry, parse_questions_response, questions_prompt as preposition_prompt


def test_english_prompts_request_explanations_and_other_languages_translations():
    entry = Entry(term="to bring about", definition="To cause something to happen.")
    for prompt in (multiple_choice_questions_prompt([(entry, [])], Vocabulary.ENGLISH, CEFRLevel.C1),
                   questions_prompt([entry], Vocabulary.ENGLISH, CEFRLevel.C1)):
        assert "explanation" in prompt and "not a repetition" in prompt
    assert "English translation" in questions_prompt([entry], Vocabulary.GERMAN, CEFRLevel.C1)
    assert "not the sentence itself" in preposition_prompt([], CEFRLevel.C1, Vocabulary.ENGLISH)


def test_connect_replaces_repeated_english_sentence_with_definition():
    entry = PrepositionEntry(term="scowl", definition="Look angry.", prepositions=["at"])
    sentence = "The teacher scowled at the noisy students."
    body = dumps({"questions": [{"id": 1, "question": "The teacher scowled _____ the noisy students.",
        "correct_answer": "at", "complete_sentence": sentence, "english_translation": sentence,
        "hint": "The teacher gave the students an angry look."}]})
    assert parse_questions_response(body, [entry], Vocabulary.ENGLISH)[0].english_translation == "Look angry."
