from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app

HISTORY: Path = Path(__file__).resolve().parent.parent / "vocabulary" / "history" / "history.db"


@pytest.fixture(scope="module")
def client():
    history_ = HISTORY.read_bytes()
    with TestClient(create_app(demo_=True)) as client_:
        yield client_
    assert HISTORY.read_bytes() == history_, "demo mode must not write the practice history"


@pytest.fixture(scope="module")
def meta(client):
    return client.get("/api/meta").json()


def test_meta_describes_languages_and_defaults(meta):
    assert meta["demo"] is True
    assert meta["blank"] == "_____"
    assert meta["levels"] == ["A1", "A2", "B1", "B2", "C1", "C2"]
    assert {language_["code"] for language_ in meta["languages"]} == {"EN", "DE", "FR"}
    assert set(meta["defaults"]) >= {"language", "level", "questions", "sentences", "revise", "secondsPerQuestion"}

    german_ = next(language_ for language_ in meta["languages"] if language_["code"] == "DE")
    assert german_["supportLanguage"] == "English"
    english_ = next(language_ for language_ in meta["languages"] if language_["code"] == "EN")
    assert english_["supportLanguage"] == "French"
    assert [file_["number"] for file_ in german_["files"]] == list(range(1, len(german_["files"]) + 1))
    assert german_["latest"] == [file_["number"] for file_ in german_["files"]][-2:]
    assert all(file_["terms"] > 0 for file_ in german_["files"])


@pytest.mark.parametrize("files_", ["latest", "all", 1])
def test_quiz_returns_questions_with_one_correct_choice(client, files_):
    response_ = client.post("/api/quiz", json={"language": "DE", "level": "C1", "count": 3, "files": files_})
    assert response_.status_code == 200
    body_ = response_.json()
    assert body_["source"]
    assert len(body_["questions"]) == 3
    for question_ in body_["questions"]:
        assert question_["term"]
        assert "_____" in question_["question"]
        assert len(question_["choices"]) == len(question_["choicesTranslations"]) == 4
        assert question_["choices"][question_["correctChoice"]] == question_["term"]


def test_typed_questions_and_checks(client):
    response_ = client.post("/api/typed", json={"language": "DE", "count": 2, "files": "latest"})
    assert response_.status_code == 200
    question_ = response_.json()["questions"][0]
    assert question_["question"].count("_____") == 1

    correct_ = client.post("/api/typed/check", json={"language": "DE", "question": question_,
                                                     "answer": f"  {question_['correctAnswer']} "}).json()
    assert correct_["verdict"] == "correct"
    assert correct_["notice"] is None

    wrong_form_ = client.post("/api/typed/check", json={"language": "DE", "question": question_,
                                                        "answer": question_["correctAnswer"].upper()}).json()
    assert wrong_form_["verdict"] == "wrong_form"

    wrong_ = client.post("/api/typed/check", json={"language": "DE", "question": question_,
                                                   "answer": "Unsinn"}).json()
    assert wrong_["verdict"] == "wrong_word"
    assert wrong_["correctedAnswer"] == question_["correctAnswer"]


def test_writing_rounds_and_check(client):
    response_ = client.post("/api/writing", json={"language": "DE", "count": 3, "files": "latest"})
    assert response_.status_code == 200
    rounds_ = response_.json()["rounds"]
    assert len(rounds_) == 3
    assert all(len(round_) == 2 and all(term_["term"] and term_["fileName"] for term_ in round_)
               for round_ in rounds_)

    correction_ = client.post("/api/writing/check", json={"language": "DE", "terms": rounds_[0],
                                                          "sentence": "Ein ganz anderer Satz."}).json()
    assert correction_["minimalCorrection"] == "Ein ganz anderer Satz."
    assert [check_["term"] for check_ in correction_["terms"]] == [term_["term"] for term_ in rounds_[0]]


@pytest.mark.parametrize("body_, status_", [
    ({"language": "DE", "count": 0}, 422),
    ({"language": "DE", "count": 51}, 422),
    ({"language": "XX", "count": 2}, 422),
    ({"language": "DE", "count": 2, "level": "D1"}, 422),
    ({"language": "DE", "count": 2, "files": "newest"}, 422),
    ({"language": "DE", "count": 2, "files": 999}, 400),
])
def test_invalid_requests_are_rejected(client, body_, status_):
    for endpoint_ in ("/api/quiz", "/api/typed", "/api/writing"):
        response_ = client.post(endpoint_, json=body_)
        assert response_.status_code == status_
        assert response_.json()["detail"]


def test_empty_answers_are_rejected(client):
    question_ = client.post("/api/typed", json={"language": "DE", "count": 1}).json()["questions"][0]
    assert client.post("/api/typed/check", json={"language": "DE", "question": question_,
                                                 "answer": "   "}).status_code == 400
    assert client.post("/api/typed/check", json={"language": "DE", "question": question_,
                                                 "answer": ""}).status_code == 422


def test_unknown_api_paths_are_json_404(client):
    response_ = client.get("/api/nothing/here")
    assert response_.status_code == 404
    assert "detail" in response_.json()


def test_other_paths_serve_the_frontend(client):
    response_ = client.get("/writing")
    assert response_.status_code in (200, 503)
    assert response_.headers["content-type"].startswith("text/html")


def test_demo_mode_follows_the_environment_when_the_app_is_created(monkeypatch):
    monkeypatch.setenv("LANGUAGES_DEMO", "1")
    with TestClient(create_app()) as client_:
        assert client_.get("/api/meta").json()["demo"] is True
    monkeypatch.setenv("LANGUAGES_DEMO", "0")
    with TestClient(create_app()) as client_:
        assert client_.get("/api/meta").json()["demo"] is False
