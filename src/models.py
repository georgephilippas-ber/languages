from re import compile as compile_regex
from time import monotonic
from typing import List

from src.configuration import MODEL, FALLBACK_MODELS, MODELS_CACHE_SECONDS, MIN_MODEL_GENERATION, \
    MAX_MODELS
from src.openai_integration import get_openai_client

TEXT_MODEL = compile_regex(r"^gpt-(\d+)")
SNAPSHOT = compile_regex(r"-\d{4}-\d{2}-\d{2}$|-\d{4}$")
EXCLUDED_PARTS: List[str] = ["audio", "realtime", "tts", "transcribe", "image", "search", "embedding", "instruct",
                             "moderation", "deep-research", "computer-use"]

__cached_models: List[str] = []
__cached_at: float = 0.0


def model_generation(id_: str) -> int:
    match_ = TEXT_MODEL.match(id_)
    return int(match_.group(1)) if match_ else 0


def is_text_model(id_: str) -> bool:
    return model_generation(id_) >= MIN_MODEL_GENERATION and not SNAPSHOT.search(id_) and \
        not any(part_ in id_ for part_ in EXCLUDED_PARTS)


def __with_default(models_: List[str]) -> List[str]:
    return (models_ if MODEL in models_ else [MODEL] + models_)[:MAX_MODELS]


def available_models(demo_: bool) -> List[str]:
    global __cached_models, __cached_at
    if demo_:
        return __with_default(FALLBACK_MODELS)
    if __cached_models and monotonic() - __cached_at < MODELS_CACHE_SECONDS:
        return __cached_models

    try:
        listed_ = [model_ for model_ in get_openai_client().models.list() if is_text_model(model_.id)]
        latest_ = max((model_generation(model_.id) for model_ in listed_), default=0)
        listed_.sort(key=lambda model_: (model_generation(model_.id) == latest_, model_.created), reverse=True)
        models_ = __with_default([model_.id for model_ in listed_])
    except Exception:
        return __cached_models or __with_default(FALLBACK_MODELS)

    __cached_models, __cached_at = models_, monotonic()
    return models_
