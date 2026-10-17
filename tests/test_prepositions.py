from dataclasses import asdict, replace
from json import dumps
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from src import prepositions
from src.domain import CEFRLevel, Entry, Vocabulary, LANGUAGE_CODES
from src.research import sample_weighted
from src.typed import TypedQuestion


@pytest.fixture
def question():
    return TypedQuestion(term="sich mit etwas befassen", question="Sie befasst sich heute _____ dem neuen Vorschlag.",
                         hint="She is dealing with the new proposal today.", correct_answer="mit",
                         complete_sentence="Sie befasst sich heute mit dem neuen Vorschlag.",
                         english_translation="She is dealing with the new proposal today.")


@pytest.fixture
def entry():
    return prepositions.PrepositionEntry(term="sich mit etwas befassen", grammar="mit + Dativ", prepositions=["mit"])


@pytest.fixture
def client():
    with TestClient(create_app()) as client_:
        yield client_


def model_response(monkeypatch, body_):
    calls_ = []

    def create(**kwargs_):
        calls_.append(kwargs_)
        return SimpleNamespace(output_text=body_)

    monkeypatch.setattr(prepositions, "get_openai_client",
                        lambda: SimpleNamespace(responses=SimpleNamespace(create=create)))
    return calls_


@pytest.mark.parametrize("language_, term_, sentence_, answer_, hint_", [
    ("DE", "sich mit etwas befassen", "Sie befasst sich heute _____ dem neuen Vorschlag.", "mit",
     "She is dealing with the new proposal today."),
    ("FR", "se pencher", "Il se penche _____ la table pour mieux voir le document.", "sur",
     "He leans over the table to see the document better."),
    ("EN", "scowl", "The teacher scowled _____ the noisy students during the lesson.", "at",
     "The teacher gave the noisy students an angry look."),
])
@pytest.mark.parametrize("files_", ["latest", "all", 1])
def test_questions_and_grading_through_the_api(client, monkeypatch, files_, language_, term_, sentence_, answer_, hint_):
    vocabulary_ = LANGUAGE_CODES[language_]
    entry_ = prepositions.PrepositionEntry(term=term_, prepositions=[answer_])
    complete_ = sentence_.replace("_____", answer_)
    question_ = TypedQuestion(term=term_, question=sentence_, hint=hint_, correct_answer=answer_,
                              complete_sentence=complete_,
                              english_translation=complete_ if vocabulary_ == Vocabulary.ENGLISH else hint_)
    monkeypatch.setattr(prepositions, "eligible_entries", lambda *args_: {term_: (entry_, 0)})
    monkeypatch.setattr(prepositions, "sample_", lambda *args_: [entry_])
    calls_ = model_response(monkeypatch, dumps({"questions": [{"id": 1, **asdict(question_)}]}))
    response_ = client.post("/api/prepositions", json={"language": language_, "level": "B2", "count": 1, "files": files_})
    assert response_.status_code == 200
    assert response_.json()["source"]
    questions_ = response_.json()["questions"]
    assert [item_["question"] for item_ in questions_] == [sentence_]
    assert vocabulary_.name.capitalize() in calls_[0]["input"]
    for answer_given_, verdict_ in [(answer_.upper(), "correct"), ("Unsinn", "wrong_word")]:
        model_response(monkeypatch, dumps({"verdict": verdict_, "corrected_answer": answer_}))
        checked_ = client.post("/api/prepositions/check",
                               json={"language": language_, "question": questions_[0], "answer": answer_given_})
        assert checked_.status_code == 200
        assert checked_.json()["verdict"] == verdict_


@pytest.mark.parametrize("language_", ["ES", "invalid"])
def test_unsupported_language_in_generation_and_grading(client, question, language_):
    assert client.post("/api/prepositions", json={"language": language_, "count": 1}).status_code == 422
    assert client.post("/api/prepositions/check", json={"language": language_, "question": asdict(question),
                                                       "answer": "mit"}).status_code == 422


@pytest.mark.parametrize("fields_, status_", [({"count": 0}, 422), ({"count": 51}, 422), ({"level": "D1"}, 422),
                                             ({"files": 999}, 400), ({"files": "invalid"}, 422)])
def test_invalid_setup(client, fields_, status_):
    assert client.post("/api/prepositions", json={"language": "DE", "count": 1, **fields_}).status_code == status_


def test_empty_answer_and_non_preposition_question_rejected(client, question):
    assert client.post("/api/prepositions/check", json={"language": "DE", "question": asdict(question),
                                                       "answer": "   "}).status_code == 400
    bad_ = replace(question, correct_answer="befassen")
    assert client.post("/api/prepositions/check", json={"language": "DE", "question": asdict(bad_),
                                                       "answer": "befassen"}).status_code == 400


def test_eligibility_reads_verb_notes_and_excludes_infinitive_zu(monkeypatch):
    entries_ = [Entry(term="die Bindung", grammar="Feminine noun."),
                Entry(term="zögern", grammar="zögern, etwas zu tun"),
                Entry(term="die Freude", grammar="über jemanden/etwas (Akkusativ)")]
    monkeypatch.setattr(prepositions, "parse_vocabulary_to_dict", lambda *args_: {e_.term: (e_, 0) for e_ in entries_})
    monkeypatch.setattr(prepositions, "read_library_file", lambda *args_: "## die Bindung\n\n**Verb:** binden "
                        "(reflexive; **an/auf + Akkusativ**, **mit + Dativ**).\n\n**Example:** x")
    eligible_ = prepositions.eligible_entries([1])
    assert eligible_["die Bindung"][0].prepositions == ["an", "auf", "mit"]
    assert eligible_["die Freude"][0].prepositions == ["über"]
    assert "zögern" not in eligible_


def test_generated_response_keeps_only_valid_preposition_questions(entry, question):
    good_ = {"id": 1, **{k_: v_ for k_, v_ in asdict(question).items() if k_ not in ("term", "hint")}}
    bad_ = [{**good_, "id": True}, {**good_, "id": 999}, "broken", None,
            {**good_, "correct_answer": "befassen"}, {**good_, "correct_answer": "im"},
            {**good_, "correct_answer": "mit dem"}, {**good_, "correct_answer": "auf"},
            {**good_, "english_translation": ""}, {**good_, "complete_sentence": "Unrelated sentence."},
            {**good_, "question": "Sie befasst sich mit dem Vorschlag."}]
    questions_ = prepositions.parse_questions_response(dumps({"questions": [*bad_, good_, good_]}), [entry])
    assert questions_ == [question]


@pytest.mark.parametrize("sentence_, answer_", [("Sie versucht _____ arbeiten.", "zu"),
                                               ("Sie macht die Tür _____ .", "zu"),
                                               ("Sie _____gibt ihm die Unterlagen.", "über")])
def test_infinitive_particle_and_prefix_are_not_preposition_questions(question, sentence_, answer_):
    bad_ = replace(question, question=sentence_, correct_answer=answer_,
                   complete_sentence=sentence_.replace("_____", answer_))
    with pytest.raises(ValueError):
        prepositions.validate_question(bad_)


def test_generation_uses_shared_weighting_and_records_only_valid_questions(monkeypatch, entry, question):
    population_ = {entry.term: (entry, 0)}
    monkeypatch.setattr(prepositions, "eligible_entries", lambda files_, vocabulary_: population_ if files_ == [3] else {})
    monkeypatch.setattr(prepositions, "retrieve_used_terms", lambda vocabulary_: ["older term"])
    sampled_ = []

    def sample(population_arg_, seen_, count_, alpha_):
        sampled_.append((population_arg_, seen_, count_, alpha_))
        return [entry]

    monkeypatch.setattr(prepositions, "sample_", sample)
    recorded_ = []
    monkeypatch.setattr(prepositions, "insert_term", lambda *args_: recorded_.append(args_))
    item_ = {"id": 1, **asdict(question)}
    calls_ = model_response(monkeypatch, dumps({"questions": [item_]}))
    result_ = prepositions.construct_questions(CEFRLevel.B1, 1, [3])
    assert result_ == [question]
    assert sampled_ == [(population_, ["older term"], 1, prepositions.UNSEEN_ALPHA)]
    assert recorded_ == [(entry.term, Vocabulary.GERMAN)]
    assert 'B1' in calls_[0]["input"] and 'prepositions' in calls_[0]["input"]
    recorded_.clear()
    model_response(monkeypatch, dumps({"questions": [{**item_, "correct_answer": "noun"}]}))
    assert prepositions.construct_questions(CEFRLevel.B1, 1, [3]) == []
    assert recorded_ == []


def test_no_eligible_terms_does_not_call_model(client, monkeypatch):
    monkeypatch.setattr(prepositions, "eligible_entries", lambda files_, vocabulary_: {})
    calls_ = model_response(monkeypatch, "unused")
    response_ = client.post("/api/prepositions", json={"language": "DE", "count": 1})
    assert response_.status_code == 400
    assert "Choose another file" in response_.json()["detail"]
    assert calls_ == []


@pytest.mark.parametrize("answer_, verdict_, corrected_", [("mit", "correct", "mit"), ("MIT", "correct", "MIT"),
                                                            ("mitt", "wrong_form", "mit"), ("auf", "correct", "auf")])
def test_model_correction_and_valid_alternative(monkeypatch, question, answer_, verdict_, corrected_):
    model_response(monkeypatch, dumps({"verdict": verdict_, "corrected_answer": corrected_, "comment": "Case note."}))
    correction_, notice_ = prepositions.check_answer(question, answer_)
    assert correction_.verdict == verdict_ and correction_.corrected_answer == corrected_
    assert notice_ is None


@pytest.mark.parametrize("response_", ['not json', '[]', '{"verdict":"correct","corrected_answer":"mit dem"}',
                                       '{"verdict":"correct","corrected_answer":"mit"}'])
def test_bad_model_correction_falls_back_without_accepting_non_preposition(monkeypatch, question, response_):
    model_response(monkeypatch, response_)
    correction_, notice_ = prepositions.check_answer(question, "mit dem")
    assert correction_.verdict == "wrong_word"
    assert correction_.corrected_answer == "mit"
    assert notice_


def test_zero_weight_eligible_pool_still_samples():
    assert list(sample_weighted(["only term"], 4, [0])) == ["only term"] * 4


@pytest.mark.parametrize("vocabulary_, term_, grammar_, expected_", [
    (Vocabulary.ENGLISH, "scowl at someone", "Regular verb: *scowl at someone*.", ["at"]),
    (Vocabulary.ENGLISH, "agree", "Use *agree with someone* and *agree to the proposal*.", ["to", "with"]),
    (Vocabulary.ENGLISH, "to work", "Infinitive: *to work*.", []),
    (Vocabulary.FRENCH, "se pencher sur quelque chose", "Use *se pencher sur la table*.", ["sur"]),
    (Vocabulary.FRENCH, "parler", "Use *parler à quelqu’un* or *parler de quelque chose*.", ["de", "à"]),
    (Vocabulary.FRENCH, "commencer à travailler", "Use *commencer à travailler*.", []),
    (Vocabulary.FRENCH, "essayer de partir", "Use *essayer de partir*.", []),
])
def test_language_specific_eligibility(monkeypatch, vocabulary_, term_, grammar_, expected_):
    entry_ = Entry(term=term_, grammar=grammar_)
    monkeypatch.setattr(prepositions, "parse_vocabulary_to_dict", lambda language_, files_: {term_: (entry_, 0)})
    monkeypatch.setattr(prepositions, "read_library_file", lambda language_, number_: f"## {term_}\n\n**Grammar:** {grammar_}")
    entries_ = prepositions.eligible_entries([1], vocabulary_)
    assert (entries_[term_][0].prepositions if entries_ else []) == expected_


@pytest.mark.parametrize("vocabulary_, sentence_, answer_", [
    (Vocabulary.ENGLISH, "She wants _____ work.", "to"),
    (Vocabulary.ENGLISH, "She gave _____ .", "up"),
    (Vocabulary.ENGLISH, "She scowled _____ the students.", "mit"),
    (Vocabulary.FRENCH, "Elle parvient _____ ouvrir la porte.", "à"),
    (Vocabulary.FRENCH, "Elle parle _____ le professeur.", "à"),
    (Vocabulary.FRENCH, "Elle revient _____ les magasins.", "de"),
    (Vocabulary.FRENCH, "Elle parle _____ professeur.", "au"),
])
def test_invalid_non_german_questions(question, vocabulary_, sentence_, answer_):
    question_ = replace(question, question=sentence_, correct_answer=answer_,
                        complete_sentence=sentence_.replace("_____", answer_))
    with pytest.raises(ValueError):
        prepositions.validate_question(question_, vocabulary_)


@pytest.mark.parametrize("vocabulary_, term_, sentence_, answer_, hint_", [
    (Vocabulary.FRENCH, "se pencher", "Il se penche _____ la table pour mieux voir le document.", "sur",
     "He leans over the table to see the document better."),
    (Vocabulary.ENGLISH, "scowl", "The teacher scowled _____ the noisy students during the lesson.", "at",
     "The teacher gave the noisy students an angry look."),
])
def test_generation_and_correction_use_selected_language(monkeypatch, vocabulary_, term_, sentence_, answer_, hint_):
    entry_ = prepositions.PrepositionEntry(term=term_, prepositions=[answer_])
    question_ = TypedQuestion(term=term_, question=sentence_, hint=hint_, correct_answer=answer_,
                              complete_sentence=sentence_.replace("_____", answer_),
                              english_translation=sentence_.replace("_____", answer_) if vocabulary_ == Vocabulary.ENGLISH else hint_)
    selected_ = []
    monkeypatch.setattr(prepositions, "eligible_entries", lambda files_, language_: selected_.append(language_) or {term_: (entry_, 0)})
    monkeypatch.setattr(prepositions, "retrieve_used_terms", lambda language_: selected_.append(language_) or [])
    monkeypatch.setattr(prepositions, "sample_", lambda *args_: [entry_])
    recorded_ = []
    monkeypatch.setattr(prepositions, "insert_term", lambda *args_: recorded_.append(args_))
    calls_ = model_response(monkeypatch, dumps({"questions": [{"id": 1, **asdict(question_)}]}))
    assert prepositions.construct_questions(CEFRLevel.B2, 1, [1], vocabulary_=vocabulary_) == [question_]
    assert selected_ == [vocabulary_, vocabulary_]
    assert recorded_ == [(term_, vocabulary_)]
    assert vocabulary_.name.capitalize() in calls_[0]["input"]
    calls_ = model_response(monkeypatch, dumps({"verdict": "correct", "corrected_answer": answer_}))
    correction_, notice_ = prepositions.check_answer(question_, answer_, vocabulary_=vocabulary_)
    assert correction_.verdict == "correct" and notice_ is None
    assert f"Check a {vocabulary_.name.capitalize()} PREPOSITION" in calls_[0]["input"]
    model_response(monkeypatch, dumps({"verdict": "correct", "corrected_answer": "mit"}))
    correction_, notice_ = prepositions.check_answer(question_, "mit", vocabulary_=vocabulary_)
    assert correction_.verdict == "wrong_word" and notice_


def test_english_hint_cannot_reveal_answer():
    entry_ = prepositions.PrepositionEntry(term="scowl", prepositions=["at"])
    item_ = {"id": 1, "question": "She scowls _____ the students.", "correct_answer": "at",
             "complete_sentence": "She scowls at the students.", "english_translation": "She scowls at the students."}
    for hint_ in (None, "", "She looks angrily at the students."):
        assert prepositions.parse_questions_response(dumps({"questions": [{**item_, "hint": hint_}]}),
                                                      [entry_], Vocabulary.ENGLISH) == []
