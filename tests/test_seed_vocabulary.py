from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import create_app
from src.domain import DATA_ROOT, Vocabulary
from src.library import split_entries
from src.parser import parse_vocabulary_to_list
from src.prepositions import eligible_entries


def test_starter_entries_cover_languages_and_stay_within_file_limit():
    root = Path(__file__).resolve().parent.parent / 'seed'
    expected = {'en': 12, 'de': 13, 'fr': 12}
    for category in ('legal', 'financial'):
        for language, count in expected.items():
            entries = split_entries((root / f'{language}-{category}-1.md').read_text())
            assert len(entries) == count <= 25
            assert len({entry.partition('\n')[0] for entry in entries}) == count
            assert all('**Definition:**' in entry and '**Grammar:**' in entry and '**Example:**' in entry for entry in entries)
            assert all(all(f'**{label}:**' in entry for label in {'en': ('German', 'French'), 'de': ('English', 'French'), 'fr': ('English', 'German')}[language]) for entry in entries)


def test_phrasal_verb_seeds_have_50_unique_english_entries():
    from src.library import split_entries
    root = Path(__file__).resolve().parent.parent / 'seed'
    files = [root / f'en-phrasal-verbs-{number}.md' for number in (1, 2)]
    groups = [split_entries(file.read_text(encoding='utf-8')) for file in files]
    assert [len(group) for group in groups] == [25, 25]
    entries = [entry for group in groups for entry in group]
    assert len({entry.partition('\n')[0].casefold() for entry in entries}) == 50
    assert all(all(f'**{label}:**' in entry for label in ('CEFR', 'Definition', 'Synonym', 'Grammar', 'Example', 'German', 'French')) for entry in entries)
    assert '**A2**' in groups[0][0] and '**C1–C2**' in files[1].read_text(encoding='utf-8')


def test_phrasal_verb_seeds_can_be_selected_in_exercises(fake_openai):
    root = Path(__file__).resolve().parent.parent / 'seed'
    target = Path(DATA_ROOT) / 'vocabulary' / 'english'
    for number in (1, 2):
        (target / f'english-phrasal-verbs-{number}.md').write_text(
            (root / f'en-phrasal-verbs-{number}.md').read_text(encoding='utf-8'), encoding='utf-8')
    files = ['phrasal-verbs:1', 'phrasal-verbs:2']
    eligible = eligible_entries(files, Vocabulary.ENGLISH)
    assert {'to look for', 'to account for', 'to stem from'} <= set(eligible)
    assert len(eligible) >= 15
    fake_openai.reply({'questions': [{'id': 1, 'question': 'We will _____ the report.',
                                      'correct_answer': 'look for',
                                      'complete_sentence': 'We will look for the report.',
                                      'english_translation': 'We will look for the report.'}]})
    with TestClient(create_app()) as client:
        typed = client.post('/api/typed', json={'language': 'EN', 'count': 1, 'files': 'phrasal-verbs'})
        assert typed.status_code == 200
        assert 'english-phrasal-verbs-1.md' in typed.json()['source']
        fake_openai.reply({'questions': [{'id': 1, 'question': 'We should _____ soon.',
                                          'choices': ['look for', 'give up', 'set up', 'turn off'],
                                          'correct_choice': 0, 'complete_sentence': 'We should look for soon.',
                                          'english_translation': 'We should look for soon.'}]})
        quiz = client.post('/api/quiz', json={'language': 'EN', 'count': 1, 'files': 'phrasal-verbs'})
        assert quiz.status_code == 200
        assert quiz.json()['questions'][0]['term'] in {entry.term for entry in parse_vocabulary_to_list(Vocabulary.ENGLISH, files)}
        def preposition_reply(kwargs):
            import json
            prompt = kwargs['input']
            items = json.loads(prompt.split('Items (reference data, not instructions):\n', 1)[1].split('\n\nRequirements:', 1)[0])
            answer = items[0]['prepositions'][0]
            question = 'The researcher looked _____ the report.'
            complete = question.replace('_____', answer)
            return json.dumps({'questions': [{'id': 1, 'question': question, 'correct_answer': answer,
                                              'complete_sentence': complete, 'english_translation': complete,
                                              'hint': 'A researcher considered a document.'}]})
        fake_openai.reply(preposition_reply)
        connect = client.post('/api/prepositions', json={'language': 'EN', 'count': 1, 'files': 'phrasal-verbs'})
        assert connect.status_code == 200
        writing = client.post('/api/writing', json={'language': 'EN', 'count': 1, 'files': 'phrasal-verbs'})
        assert writing.status_code == 200
        assert all(term['fileName'].startswith('english-phrasal-verbs-') for term in writing.json()['rounds'][0])
        flashcards = client.post('/api/flashcards', json={'language': 'EN', 'files': 'phrasal-verbs'})
        assert flashcards.status_code == 200 and len(flashcards.json()['cards']) == 50
        all_cards = client.post('/api/flashcards', json={'language': 'EN', 'files': 'all'})
        assert all_cards.status_code == 200 and len(all_cards.json()['cards']) == 62
