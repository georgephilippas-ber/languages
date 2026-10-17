import sys
from json import dumps
from os import environ
from pathlib import Path
from shutil import copytree, rmtree
from tempfile import mkdtemp
from types import SimpleNamespace

import pytest

ROOT: Path = Path(__file__).resolve().parent.parent
VOCABULARY: Path = ROOT / "vocabulary"
DATA: Path = Path(mkdtemp(prefix="languages-tests-"))

copytree(VOCABULARY, DATA / "vocabulary")
environ["LANGUAGES_DATA"] = str(DATA)


def __snapshot():
    return {path_: path_.read_bytes() for path_ in VOCABULARY.rglob("*") if path_.is_file()}


class FakeOpenAI:
    def __init__(self):
        self.calls = []
        self.models_ = [SimpleNamespace(id="gpt-6.1-sol", created=3), SimpleNamespace(id="gpt-6-luna", created=2),
                        SimpleNamespace(id="gpt-5.5", created=1)]
        self.reply_ = lambda kwargs_: "{}"
        self.responses = SimpleNamespace(create=self.__create)
        self.models = SimpleNamespace(list=lambda: list(self.models_))

    def __create(self, **kwargs_):
        self.calls.append(kwargs_)
        return SimpleNamespace(output_text=self.reply_(kwargs_))

    def reply(self, reply_):
        if callable(reply_):
            self.reply_ = reply_
        else:
            self.reply_ = lambda kwargs_: reply_ if isinstance(reply_, str) else dumps(reply_, ensure_ascii=False)


@pytest.fixture(scope="session", autouse=True)
def repository_data_is_untouched():
    before_ = __snapshot()
    yield
    assert __snapshot() == before_, "the tests must not write the repository's vocabulary or practice history"
    rmtree(DATA, ignore_errors=True)


@pytest.fixture(autouse=True)
def fresh_data():
    yield
    rmtree(DATA / "vocabulary")
    copytree(VOCABULARY, DATA / "vocabulary")


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch):
    fake_ = FakeOpenAI()
    for name_, module_ in list(sys.modules.items()):
        if name_.startswith("src.") and hasattr(module_, "get_openai_client"):
            monkeypatch.setattr(module_, "get_openai_client", lambda: fake_)

    return fake_
