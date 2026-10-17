from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from httpx import Request
from openai import APIConnectionError

from backend.app import create_app
from src import models
from src.asking import OFF_TOPIC_ANSWER
from src.configuration import MODEL
from src.database import retrieve_used_terms
from src.domain import Vocabulary
from src.library import library_file_path

ENTRY: str = """## die Krähe

**CEFR:** roughly **B1**.

**Definition:** A large black bird.

**Synonym:** **der Rabe** (close).

**Grammar:** Feminine noun: *die Krähe, die Krähen*.

**Example:** *Eine Krähe saß auf dem Zaun.* — "A crow sat on the fence."

**English:** crow · **French:** la corneille

Useful nuance: Crows are proverbially clever."""

QUESTION: dict = {"term": "die Krähe", "question": "Eine _____ saß auf dem Zaun.", "hint": "crow",
                  "correctAnswer": "Krähe", "completeSentence": "Eine Krähe saß auf dem Zaun.",
                  "englishTranslation": "A crow sat on the fence."}


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as client_:
        yield client_


@pytest.fixture(scope="module")
def meta(client):
    return client.get("/api/meta").json()


def __german(meta_):
    return next(language_ for language_ in meta_["languages"] if language_["code"] == "DE")


def __quiz_questions(count_):
    return {"questions": [{"id": i_, "question": f"Satz {i_} mit _____.", "choices": ["a", "b", "c", "d"],
                           "correct_choice": 0, "complete_sentence": f"Satz {i_} mit a.",
                           "english_translation": f"Sentence {i_} with a.",
                           "choices_translations": ["a", "b", "c", "d"]} for i_ in range(1, count_ + 1)]}


def test_meta_describes_languages_and_defaults(meta):
    assert "demo" not in meta
    assert meta["blank"] == "_____"
    assert meta["levels"] == ["A1", "A2", "B1", "B2", "C1", "C2"]
    assert {language_["code"] for language_ in meta["languages"]} == {"EN", "DE", "FR"}
    assert set(meta["defaults"]) >= {"language", "level", "questions", "sentences", "revise", "secondsPerQuestion"}

    german_ = __german(meta)
    assert german_["supportLanguage"] == "English"
    english_ = next(language_ for language_ in meta["languages"] if language_["code"] == "EN")
    assert english_["supportLanguage"] == "French"
    assert [file_["number"] for file_ in german_["files"]] == list(range(1, len(german_["files"]) + 1))
    assert german_["latest"] == [file_["number"] for file_ in german_["files"]][-2:]
    assert all(file_["terms"] > 0 for file_ in german_["files"])


@pytest.mark.parametrize("files_", ["latest", "all", "current", 1])
def test_quiz_asks_the_model_and_records_the_terms(client, fake_openai, files_):
    fake_openai.reply(__quiz_questions(3))
    response_ = client.post("/api/quiz", json={"language": "DE", "level": "C1", "count": 3, "files": files_})
    assert response_.status_code == 200
    body_ = response_.json()
    assert body_["source"]
    assert len(body_["questions"]) == 3
    terms_ = [question_["term"] for question_ in body_["questions"]]
    assert all(term_ in fake_openai.calls[0]["input"] for term_ in terms_)
    assert fake_openai.calls[0]["model"] == MODEL
    assert set(terms_) <= set(retrieve_used_terms(Vocabulary.GERMAN))


def test_quiz_without_usable_questions_is_a_502(client, fake_openai):
    fake_openai.reply("not json")
    response_ = client.post("/api/quiz", json={"language": "DE", "count": 2})
    assert response_.status_code == 502
    assert response_.json()["detail"]


def test_typed_questions_and_checks(client, fake_openai):
    fake_openai.reply({"questions": [{"id": i_, "question": "Eine _____ saß auf dem Zaun.", "correct_answer": "Krähe",
                                      "complete_sentence": "Eine Krähe saß auf dem Zaun.",
                                      "english_translation": "A crow sat on the fence."} for i_ in (1, 2)]})
    response_ = client.post("/api/typed", json={"language": "DE", "count": 2, "files": "latest"})
    assert response_.status_code == 200
    question_ = response_.json()["questions"][0]
    assert question_["question"].count("_____") == 1
    assert question_["hint"]
    assert "choices" not in question_

    fake_openai.reply({"verdict": "correct", "corrected_answer": "Krähe", "errors": [], "comment": "Right.",
                       "suggestions": ["die Krähen"]})
    correct_ = client.post("/api/typed/check", json={"language": "DE", "question": question_,
                                                     "answer": "  Krähe "}).json()
    assert correct_["verdict"] == "correct" and correct_["notice"] is None
    assert correct_["suggestions"] == ["die Krähen"]
    assert '"""Krähe"""' in fake_openai.calls[-1]["input"]

    fake_openai.reply("not json")
    fallback_ = client.post("/api/typed/check", json={"language": "DE", "question": question_,
                                                      "answer": "Unsinn"}).json()
    assert fallback_["verdict"] == "wrong_word" and fallback_["notice"]
    assert fallback_["correctedAnswer"] == question_["correctAnswer"]


def test_writing_rounds_and_check(client, fake_openai):
    response_ = client.post("/api/writing", json={"language": "DE", "count": 3, "files": "latest"})
    assert response_.status_code == 200
    rounds_ = response_.json()["rounds"]
    assert len(rounds_) == 3
    assert all(len(round_) == 2 and all(term_["term"] and term_["fileName"] for term_ in round_)
               for round_ in rounds_)
    assert fake_openai.calls == []

    fake_openai.reply({"is_correct": True, "minimal_correction": "Ein ganz anderer Satz!",
                       "natural_version": "Ein völlig anderer Satz.", "translation": "A different sentence.",
                       "terms": [{"used": False, "used_correctly": False, "comment": "Missing."}] * 2,
                       "corrections": [{"original": ".", "corrected": "!", "explanation": "Emphasis."}],
                       "feedback": "Use the terms.", "level": "b1", "level_comment": "Simple."})
    correction_ = client.post("/api/writing/check", json={"language": "DE", "level": "C1", "terms": rounds_[0],
                                                          "sentence": "Ein ganz anderer Satz."}).json()
    assert correction_["isCorrect"] is False
    assert correction_["minimalCorrection"] == "Ein ganz anderer Satz!"
    assert correction_["targetLevel"] == "C1" and correction_["level"] == "B1"
    assert [check_["term"] for check_ in correction_["terms"]] == [term_["term"] for term_ in rounds_[0]]


@pytest.mark.parametrize("body_, status_", [
    ({"language": "DE", "count": 0}, 422),
    ({"language": "DE", "count": 51}, 422),
    ({"language": "XX", "count": 2}, 422),
    ({"language": "DE", "count": 2, "level": "D1"}, 422),
    ({"language": "DE", "count": 2, "files": "newest"}, 422),
    ({"language": "DE", "count": 2, "files": 999}, 400),
])
def test_invalid_requests_are_rejected(client, fake_openai, body_, status_):
    for endpoint_ in ("/api/quiz", "/api/typed", "/api/writing"):
        response_ = client.post(endpoint_, json=body_)
        assert response_.status_code == status_
        assert response_.json()["detail"]
    assert fake_openai.calls == []


def test_empty_answers_are_rejected(client):
    assert client.post("/api/typed/check", json={"language": "DE", "question": QUESTION,
                                                 "answer": "   "}).status_code == 400
    assert client.post("/api/typed/check", json={"language": "DE", "question": QUESTION,
                                                 "answer": ""}).status_code == 422


def test_unknown_api_paths_are_json_404(client):
    response_ = client.get("/api/nothing/here")
    assert response_.status_code == 404
    assert "detail" in response_.json()


def test_other_paths_serve_the_frontend(client):
    response_ = client.get("/writing")
    assert response_.status_code in (200, 503)
    assert response_.headers["content-type"].startswith("text/html")


def test_define_and_save_entries(client, fake_openai, meta):
    fake_openai.reply({"entry": ENTRY, "gloss": "crow"})
    entry_ = client.post("/api/entries/define", json={"language": "DE", "term": "  die   Krähe "}).json()
    assert '"""die Krähe"""' in fake_openai.calls[0]["input"]
    assert entry_["term"] == "die Krähe" and entry_["gloss"] == "crow"
    assert entry_["markdown"].startswith("## die Krähe\n\n**CEFR:**")

    latest_ = __german(meta)["files"][-1]
    result_ = client.post("/api/entries/save", json={"language": "DE", "entries": [entry_["markdown"]] * 30}).json()
    assert "demo" not in result_
    assert len(result_["saved"]) == 30
    first_ = result_["saved"][0]
    if latest_["terms"] < 25:
        assert first_["fileName"] == latest_["name"] and first_["termsInFile"] == latest_["terms"] + 1
    assert all(saved_["termsInFile"] <= 25 for saved_ in result_["saved"])
    assert result_["fileName"] != latest_["name"]
    with open(library_file_path(Vocabulary.GERMAN, latest_["number"] + 1), encoding="utf-8") as file_:
        assert file_.read().startswith("## die Krähe\n")


def test_unreadable_definition_is_a_502(client, fake_openai):
    fake_openai.reply({"entry": "no heading"})
    response_ = client.post("/api/entries/define", json={"language": "DE", "term": "die Krähe"})
    assert response_.status_code == 502
    assert "could not be read" in response_.json()["detail"]


def test_translate(client, fake_openai):
    fake_openai.reply({"source_language": "German", "target_language": "English", "translation": "I don't care",
                       "notes": ["**mir** is dative.", "", "Informal."]})
    translation_ = client.post("/api/entries/translate", json={"language": "DE", "phrase": " Das  ist mir Wurst "}).json()
    assert '"""Das ist mir Wurst"""' in fake_openai.calls[0]["input"]
    assert translation_["sourceLanguage"] == "German" and translation_["targetLanguage"] == "English"
    assert translation_["translation"] == "I don't care"
    assert translation_["notes"] == ["**mir** is dative.", "Informal."]
    assert client.post("/api/entries/translate", json={"language": "DE", "phrase": "   "}).status_code == 400


def test_ask(client, fake_openai):
    history_ = [{"question": "What does *Wurst* mean?", "answer": "**die Wurst**: sausage."}]
    fake_openai.reply({"on_topic": True, "answer": " The dative *mir* marks the person affected. "})
    answer_ = client.post("/api/ask", json={"language": "DE", "question": " Why *mir*? ", "history": history_}).json()
    assert answer_ == {"onTopic": True, "answer": "The dative *mir* marks the person affected."}
    assert "German" in fake_openai.calls[0]["instructions"]
    assert [message_["content"] for message_ in fake_openai.calls[0]["input"]] == \
           ["What does *Wurst* mean?", "**die Wurst**: sausage.", "Why *mir*?"]

    fake_openai.reply({"on_topic": False, "answer": "Here is a recipe."})
    off_topic_ = client.post("/api/ask", json={"language": "DE", "question": "Cook me dinner."}).json()
    assert off_topic_ == {"onTopic": False, "answer": OFF_TOPIC_ANSWER}
    assert client.post("/api/ask", json={"language": "DE", "question": "   "}).status_code == 400


def test_read(client, fake_openai, meta):
    assert meta["topics"] == ["finance", "law", "physics", "engineering", "politics"]

    fake_openai.reply({"topic": "Physics", "title": " Ein neuer  Rekord ", "publication": "Die Zeit",
                       "url": "https://example.com/rekord", "summary": "Forscher melden einen neuen Rekord.",
                       "words": ["Forscher", "Rekord", "Quantencomputer"]})
    article_ = client.post("/api/read", json={"language": "DE", "topic": " Physics ", "level": "B2"}).json()
    assert article_["topic"] == "physics" and article_["title"] == "Ein neuer Rekord"
    assert article_["url"] == "https://example.com/rekord"
    assert article_["words"] == ["Forscher", "Rekord"]
    assert "B2" in fake_openai.calls[0]["instructions"]

    fake_openai.reply({"title": "Zu lang", "summary": "Wort " * 81, "words": []})
    assert client.post("/api/read", json={"language": "DE", "topic": "law"}).status_code == 502
    assert client.post("/api/read", json={"language": "DE", "topic": "gossip"}).status_code == 400
    assert client.post("/api/read", json={"language": "DE", "topic": "   "}).status_code == 400
    assert client.post("/api/read", json={"language": "DE", "topic": "law", "level": "D1"}).status_code == 422


def test_save_rejects_malformed_entries(client):
    for entry_ in ["no heading", "## term\n\nno definition", "## term\n\n**Definition:** x ## y"]:
        response_ = client.post("/api/entries/save", json={"language": "DE", "entries": [entry_]})
        assert response_.status_code == 400


def test_flashcards_and_reviews(client, meta):
    response_ = client.post("/api/flashcards", json={"language": "DE", "files": 1})
    assert response_.status_code == 200
    cards_ = response_.json()["cards"]
    assert len(cards_) == __german(meta)["files"][0]["terms"]
    card_ = cards_[0]
    assert card_["term"] and card_["fileName"] == "german-1.md"
    assert any(section_["label"] == "Definition" for section_ in card_["sections"])
    assert set(card_["intervals"]) == {"again", "hard", "good", "easy"}

    review_ = client.post("/api/flashcards/review", json={"language": "DE", "term": card_["term"],
                                                          "grade": "good"}).json()
    assert review_["state"]["repetitions"] >= 1 and review_["state"]["dueAt"]
    assert set(review_["intervals"]) == {"again", "hard", "good", "easy"}
    stored_ = next(card_after_ for card_after_ in
                   client.post("/api/flashcards", json={"language": "DE", "files": 1}).json()["cards"]
                   if card_after_["term"] == card_["term"])
    assert stored_["state"] == review_["state"]

    assert client.post("/api/flashcards", json={"language": "DE", "files": 999}).status_code == 400
    assert client.post("/api/flashcards/review", json={"language": "DE", "term": "x",
                                                       "grade": "perfect"}).status_code == 422


def test_models_lists_the_default_and_accepts_a_listed_model(client, fake_openai, monkeypatch):
    monkeypatch.setattr(models, "__cached_models", [])
    fake_openai.models_ += [SimpleNamespace(id=id_, created=0) for id_ in ("gpt-4o", "gpt-5.5-2025-08-07", "gpt-6-realtime")]
    response_ = client.get("/api/models")
    assert response_.status_code == 200
    body_ = response_.json()
    assert body_["default"] == MODEL
    assert body_["models"] == ["gpt-6.1-sol", "gpt-6-luna", "gpt-5.5"]

    fake_openai.reply({"questions": []})
    response_ = client.post("/api/typed", json={"language": "DE", "count": 1, "files": "latest"},
                            headers={"X-OpenAI-Model": "gpt-5.5"})
    assert fake_openai.calls[-1]["model"] == "gpt-5.5"
    assert response_.status_code == 502


def test_unknown_model_is_rejected(client, fake_openai):
    response_ = client.post("/api/typed", json={"language": "DE", "count": 1, "files": "latest"},
                            headers={"X-OpenAI-Model": "not-a-model"})
    assert response_.status_code == 400
    assert "not-a-model" in response_.json()["detail"]
    assert fake_openai.calls == []


def test_openai_failures_are_a_502(client, fake_openai):
    def fail(kwargs_):
        raise APIConnectionError(request=Request("POST", "https://api.openai.com/v1/responses"))

    fake_openai.reply(fail)
    response_ = client.post("/api/entries/translate", json={"language": "DE", "phrase": "Wurst"})
    assert response_.status_code == 502
    assert response_.json()["detail"].startswith("The request to OpenAI failed")
