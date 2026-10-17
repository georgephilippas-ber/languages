from dataclasses import asdict, replace
from json import dumps
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from src import articles
from src.domain import CEFRLevel, Entry, Vocabulary, LANGUAGE_CODES
from src.research import sample_weighted
from src.typed import TypedQuestion


@pytest.fixture
def question():
    return TypedQuestion(term="die Gewöhnung", question="Nach dem Umzug brauchte die Familie _____ Gewöhnung an das neue Klima.",
                         hint="After the move, the family needed getting used to the new climate.",
                         correct_answer="die", complete_sentence="Nach dem Umzug brauchte die Familie die Gewöhnung an das neue Klima.",
                         english_translation="After the move, the family needed getting used to the new climate.")


@pytest.fixture
def entry():
    return articles.ArticleEntry(term="die Gewöhnung", grammar="Feminine noun: *die Gewöhnung*.",
                                  article="die", noun="Gewöhnung")


@pytest.fixture
def client():
    with TestClient(create_app()) as client_:
        yield client_


def model_response(monkeypatch, body_):
    calls_ = []

    def create(**kwargs_):
        calls_.append(kwargs_)
        return SimpleNamespace(output_text=body_)

    monkeypatch.setattr(articles, "get_openai_client",
                        lambda: SimpleNamespace(responses=SimpleNamespace(create=create)))
    return calls_


@pytest.mark.parametrize("language_, files_", [(l_, f_) for l_ in ("DE", "FR") for f_ in ("latest", "all", 1)])
def test_questions_and_grading_through_the_api(client, monkeypatch, entry, question, language_, files_):
    vocabulary_ = LANGUAGE_CODES[language_]
    if vocabulary_ == Vocabulary.FRENCH:
        entry = articles.ArticleEntry(term="l’abîme", article="l’", noun="abîme")
        question = TypedQuestion(term="l’abîme", question="Il regardait dans _____abîme du puits.",
                                 hint="He looked into the pit.", correct_answer="l’",
                                 complete_sentence="Il regardait dans l’abîme du puits.",
                                 english_translation="He looked into the pit.")
    monkeypatch.setattr(articles, "sample_", lambda *args_: [entry])
    calls_ = model_response(monkeypatch, dumps({"questions": [{"id": 1, **asdict(question)}]}))
    response_ = client.post("/api/articles", json={"language": language_, "level": "B2", "count": 1, "files": files_})
    assert response_.status_code == 200
    assert response_.json()["source"]
    assert response_.json()["questions"] == [{"term": question.term, "question": question.question,
                                              "hint": question.hint, "correctAnswer": question.correct_answer,
                                              "completeSentence": question.complete_sentence,
                                              "englishTranslation": question.english_translation}]
    assert vocabulary_.name.capitalize() in calls_[0]["input"]
    question_ = response_.json()["questions"][0]
    for answer_, verdict_ in [(question_["correctAnswer"].upper(), "correct"), ("Unsinn", "wrong_word")]:
        model_response(monkeypatch, dumps({"verdict": verdict_, "corrected_answer": question_["correctAnswer"]}))
        checked_ = client.post("/api/articles/check",
                               json={"language": language_, "question": question_, "answer": answer_})
        assert checked_.status_code == 200
        assert checked_.json()["verdict"] == verdict_


@pytest.mark.parametrize("language_", ["ES", "invalid"])
def test_unsupported_language_in_generation_and_grading(client, question, language_):
    assert client.post("/api/articles", json={"language": language_, "count": 1}).status_code == 422
    assert client.post("/api/articles/check", json={"language": language_, "question": asdict(question),
                                                    "answer": "die"}).status_code == 422


def test_english_is_rejected_with_a_clear_error(client, monkeypatch):
    monkeypatch.setattr(articles, "eligible_entries", lambda files_, vocabulary_: {})
    calls_ = model_response(monkeypatch, "unused")
    response_ = client.post("/api/articles", json={"language": "EN", "count": 1})
    assert response_.status_code == 400
    assert "only in German and French" in response_.json()["detail"]
    assert calls_ == []


@pytest.mark.parametrize("fields_, status_", [({"count": 0}, 422), ({"count": 51}, 422), ({"level": "D1"}, 422),
                                              ({"files": 999}, 400), ({"files": "invalid"}, 422)])
def test_invalid_setup(client, fields_, status_):
    assert client.post("/api/articles", json={"language": "DE", "count": 1, **fields_}).status_code == status_


def test_empty_answer_and_non_article_question_rejected(client, question):
    assert client.post("/api/articles/check", json={"language": "DE", "question": asdict(question),
                                                    "answer": "   "}).status_code == 400
    bad_ = replace(question, correct_answer="Gewöhnung")
    assert client.post("/api/articles/check", json={"language": "DE", "question": asdict(bad_),
                                                    "answer": "Gewöhnung"}).status_code == 400


@pytest.mark.parametrize("vocabulary_, term_, article_, noun_", [
    (Vocabulary.GERMAN, "der Drang", "der", "Drang"),
    (Vocabulary.GERMAN, "die Ausgewogenheit", "die", "Ausgewogenheit"),
    (Vocabulary.FRENCH, "le châtiment", "le", "châtiment"),
    (Vocabulary.FRENCH, "l’étalage", "l’", "étalage"),
    (Vocabulary.FRENCH, "la faillite / faillites en chaîne", "la", "faillite"),
])
def test_heading_split(vocabulary_, term_, article_, noun_):
    assert articles.split_heading(term_, vocabulary_) == (article_, noun_)


@pytest.mark.parametrize("vocabulary_, term_", [(Vocabulary.GERMAN, "zögern"), (Vocabulary.GERMAN, "etwas beachten"),
                                                (Vocabulary.FRENCH, "printanier"), (Vocabulary.FRENCH, "se pencher")])
def test_non_nouns_are_not_eligible(vocabulary_, term_):
    assert articles.split_heading(term_, vocabulary_) is None


def test_eligibility_keeps_only_nouns_with_articles(monkeypatch):
    entries_ = [Entry(term="der Drang", grammar="Masculine noun."), Entry(term="zögern", grammar="Regular verb.")]
    monkeypatch.setattr(articles, "parse_vocabulary_to_dict", lambda *args_: {e_.term: (e_, 0) for e_ in entries_})
    eligible_ = articles.eligible_entries([1])
    assert list(eligible_) == ["der Drang"]
    assert eligible_["der Drang"][0].noun == "Drang"
    assert articles.eligible_entries([1], Vocabulary.ENGLISH) == {}


def test_generated_response_keeps_only_valid_article_questions(entry, question):
    good_ = {"id": 1, **{k_: v_ for k_, v_ in asdict(question).items() if k_ not in ("term", "hint")}}
    bad_ = [{**good_, "id": True}, {**good_, "id": 999}, "broken", None,
            {**good_, "correct_answer": "Gewöhnung"}, {**good_, "correct_answer": "ein"},
            {**good_, "correct_answer": "die Gewöhnung"}, {**good_, "correct_answer": "dem"},
            {**good_, "english_translation": ""}, {**good_, "complete_sentence": "Unrelated sentence."},
            {**good_, "question": "Die Familie brauchte keine _____ mehr."},
            {**good_, "question": "Der Wagen parkt in _____ Strasse."}]
    questions_ = articles.parse_questions_response(dumps({"questions": [*bad_, good_, good_]}), [entry])
    assert questions_ == [question]


def test_elision_question_is_valid():
    question_ = TypedQuestion(term="l’abîme", question="Il regardait dans _____abîme du puits.", hint="He looked into the pit.",
                              correct_answer="l’", complete_sentence="Il regardait dans l’abîme du puits.",
                              english_translation="He looked into the pit.")
    articles.validate_question(question_, Vocabulary.FRENCH)
    with pytest.raises(ValueError):
        articles.validate_question(replace(question_, correct_answer="l"))
    with pytest.raises(ValueError):
        articles.validate_question(replace(question_, correct_answer="le"))
    with pytest.raises(ValueError):
        articles.validate_question(replace(question_, question="Il regardait dans _____ abîme du puits."))
    with pytest.raises(ValueError):
        articles.validate_question(replace(question_, question="Il regardait dans l’abîme du puits."))


def test_generation_uses_shared_weighting_and_records_only_valid_questions(monkeypatch, entry, question):
    population_ = {entry.term: (entry, 0)}
    monkeypatch.setattr(articles, "eligible_entries", lambda files_, vocabulary_: population_ if files_ == [3] else {})
    monkeypatch.setattr(articles, "retrieve_used_terms", lambda vocabulary_: ["older term"])
    sampled_ = []

    def sample(population_arg_, seen_, count_, alpha_):
        sampled_.append((population_arg_, seen_, count_, alpha_))
        return [entry]

    monkeypatch.setattr(articles, "sample_", sample)
    recorded_ = []
    monkeypatch.setattr(articles, "insert_term", lambda *args_: recorded_.append(args_))
    item_ = {"id": 1, **{k_: v_ for k_, v_ in asdict(question).items() if k_ not in ("term", "hint")}}
    calls_ = model_response(monkeypatch, dumps({"questions": [item_]}))
    result_ = articles.construct_questions(CEFRLevel.B1, 1, [3])
    assert result_ == [question]
    assert sampled_ == [(population_, ["older term"], 1, articles.UNSEEN_ALPHA)]
    assert recorded_ == [(entry.term, Vocabulary.GERMAN)]
    assert "B1" in calls_[0]["input"] and "ARTICLE" in calls_[0]["input"]
    recorded_.clear()
    model_response(monkeypatch, dumps({"questions": [{**item_, "correct_answer": "noun"}]}))
    assert articles.construct_questions(CEFRLevel.B1, 1, [3]) == []
    assert recorded_ == []


def test_generation_rejects_english(monkeypatch):
    model_response(monkeypatch, "unused")
    with pytest.raises(ValueError):
        articles.construct_questions(CEFRLevel.B1, 1, [1], vocabulary_=Vocabulary.ENGLISH)


def test_no_eligible_terms_does_not_call_model(client, monkeypatch):
    monkeypatch.setattr(articles, "eligible_entries", lambda files_, vocabulary_: {})
    calls_ = model_response(monkeypatch, "unused")
    response_ = client.post("/api/articles", json={"language": "DE", "count": 1})
    assert response_.status_code == 400
    assert "no nouns with articles" in response_.json()["detail"]
    assert calls_ == []


@pytest.mark.parametrize("answer_, verdict_, corrected_", [("die", "correct", "die"), ("DIE", "correct", "DIE"),
                                                           ("der", "wrong_word", "die")])
def test_model_correction(monkeypatch, question, answer_, verdict_, corrected_):
    model_response(monkeypatch, dumps({"verdict": verdict_, "corrected_answer": corrected_, "comment": "Gender note."}))
    correction_, notice_ = articles.check_answer(question, answer_)
    assert correction_.verdict == verdict_ and correction_.corrected_answer == corrected_
    assert notice_ is None


@pytest.mark.parametrize("response_", ['not json', '[]', '{"verdict":"correct","corrected_answer":"die Gewöhnung"}',
                                       '{"verdict":"correct","corrected_answer":"die"}'])
def test_bad_model_correction_falls_back_without_accepting_non_article(monkeypatch, question, response_):
    model_response(monkeypatch, response_)
    correction_, notice_ = articles.check_answer(question, "die Gewöhnung")
    assert correction_.verdict == "wrong_word"
    assert correction_.corrected_answer == "die"
    assert notice_


def test_check_answer_rejects_english(question):
    with pytest.raises(ValueError):
        articles.check_answer(question, "the", vocabulary_=Vocabulary.ENGLISH)


def test_zero_weight_eligible_pool_still_samples():
    assert list(sample_weighted(["only term"], 4, [0])) == ["only term"] * 4
