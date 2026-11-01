from os import environ, fsync, replace
from pathlib import Path
from re import compile as compile_regex
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Dict, List, Optional

from dotenv import dotenv_values

from src.domain import DATA_ROOT
from src.models import reset_models
from src.openai_integration import reset_openai_client

KEY_NAME: str = "OPENAI_API_KEY"
KEY_PATTERN = compile_regex(r"^sk-[A-Za-z0-9_\-]{16,256}$")
HINT_LENGTH: int = 4

__lock = Lock()


def env_path() -> Path:
    return Path(DATA_ROOT) / ".env"


def __file_key() -> Optional[str]:
    path_ = env_path()
    return (dotenv_values(path_).get(KEY_NAME) or None) if path_.is_file() else None


def api_key_status() -> Dict[str, Optional[str] | bool]:
    file_key_ = __file_key()
    key_ = environ.get(KEY_NAME) or file_key_
    if not key_:
        return {"configured": False, "hint": None, "source": None}

    return {"configured": True, "hint": key_[-HINT_LENGTH:], "source": "file" if key_ == file_key_ else "environment"}


def normalize_api_key(key_: str) -> str:
    key_ = key_.strip().strip("\"'")
    if not KEY_PATTERN.match(key_):
        raise ValueError("This does not look like an OpenAI API key. It starts with sk- and has no spaces")

    return key_


def __with_key(lines_: List[str], key_: str) -> List[str]:
    line_ = f"{KEY_NAME}={key_}\n"
    kept_ = [existing_ for existing_ in lines_
             if existing_.split("=", 1)[0].strip().removeprefix("export ").strip() != KEY_NAME]

    if kept_ and not kept_[-1].endswith("\n"):
        kept_[-1] += "\n"

    return kept_ + [line_]


def save_api_key(key_: str) -> None:
    path_ = env_path()
    temporary_: Optional[Path] = None
    with __lock:
        path_.parent.mkdir(parents=True, exist_ok=True)
        lines_ = path_.read_text(encoding="utf-8").splitlines(keepends=True) if path_.is_file() else []
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=path_.parent, prefix=".env-", suffix=".tmp",
                                    delete=False) as file_:
                temporary_ = Path(file_.name)
                file_.writelines(__with_key(lines_, key_))
                file_.flush()
                fsync(file_.fileno())
            temporary_.chmod(0o600)
            replace(temporary_, path_)
        finally:
            if temporary_ is not None:
                temporary_.unlink(missing_ok=True)
        environ[KEY_NAME] = key_
        reset_openai_client()
        reset_models()
