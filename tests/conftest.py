import sys
from json import dumps
from os import environ
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from types import SimpleNamespace

import pytest

ROOT: Path = Path(__file__).resolve().parent.parent
DATA: Path = Path(mkdtemp(prefix="languages-tests-"))
environ["LANGUAGES_DATA"] = str(DATA)


def reset_data():
    from src.paths import initialize_data
    rmtree(DATA / "vocabulary", ignore_errors=True)
    initialize_data(DATA)
    for language, noun, pattern in (("german", "die Sache", "sich mit etwas befassen"),
                                     ("french", "la chose", "se pencher sur quelque chose"),
                                     ("english", "thing", "scowl at something")):
        entries = [f"## {noun} {i}\n\n**Definition:** A test object {i}.\n\n"
                   f"**Grammar:** Noun; {pattern}.\n\n**English:** test object {i}\n"
                   for i in range(12)]
        (DATA / "vocabulary" / language / f"{language}-1.md").write_text("\n".join(entries), encoding="utf-8")


reset_data()


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
def temporary_data():
    yield
    rmtree(DATA, ignore_errors=True)


@pytest.fixture(autouse=True)
def fresh_data():
    yield
    reset_data()


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch):
    fake_ = FakeOpenAI()
    for name_, module_ in list(sys.modules.items()):
        if name_.startswith("src.") and hasattr(module_, "get_openai_client"):
            monkeypatch.setattr(module_, "get_openai_client", lambda: fake_)

    return fake_


def pytest_addoption(parser):
    parser.addoption('--run-browser', action='store_true', help='Run isolated Chromium/Firefox workflows')
    parser.addoption('--run-packaged', action='store_true', help='Run macOS app bundle lifecycle checks')
    parser.addoption('--app-path', default=str(ROOT / 'bin/Languages.app'), help='Built app bundle to test')


def pytest_collection_modifyitems(config, items):
    for item in items:
        for marker, option in [('browser', '--run-browser'), ('packaged', '--run-packaged')]:
            if marker in item.keywords and not config.getoption(option):
                item.add_marker(pytest.mark.skip(reason=f'Use {option} to run this integration check'))
