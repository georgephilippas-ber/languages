from dataclasses import dataclass
from json import loads, JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple

from src.domain import Vocabulary, CEFRLevel
from src.openai_integration import get_openai_client, current_model, strip_code_fences

MAX_SUMMARY_WORDS: int = 80
MAX_WORDS: int = 12

TOPICS: Tuple[str, ...] = ("finance", "law", "physics", "engineering", "politics")


@dataclass
class Article:
    topic: str
    title: str
    publication: str
    summary: str
    words: List[str]
    url: str = ""


def read_instructions(vocabulary_: Vocabulary, topic_: str, cefr_level_: CEFRLevel) -> str:
    language_ = vocabulary_.name.capitalize()
    level_ = cefr_level_.name

    return f"""
You are an experienced {language_} teacher. Think of an article from the {topic_} section of a respected {language_}
publication, one that reports something currently discussed in {topic_}: the most recent such development you know.
You cannot browse; use only what you know.

Then summarize that article for a learner of {language_} at the CEFR level {level_}:

- Write the summary in {language_}, as plain prose: no lists, no headings, no code blocks. At most {MAX_SUMMARY_WORDS}
words; count them and stay under the limit.
- Write it at exactly the level {level_}: use the vocabulary and the structures a learner at that level is acquiring,
so the level of the summary matches {level_}.
- Then pick the words of the summary that carry that level: the ones a learner at exactly {level_} would be learning
from this text, at most {MAX_WORDS}, each in the exact form in which it appears in the summary.

Citations are welcome: if you know the address of the article, of the coverage it reports, or of a canonical source
it cites, put the most useful single link in "url"; otherwise set "url" to an empty string. Give the link as plain
text, not Markdown.

Return only a JSON object, with no Markdown code fences and no other text:
{{"topic": "{topic_}", "title": str, "publication": str, "url": str, "summary": str, "words": [str]}}
"title" is the article's title in {language_}, "publication" the name of the publication, "url" the link,
"summary" the summary, "words" the level words."""


ARTICLE_FORMAT: Dict[str, Any] = {
    "type": "json_schema",
    "name": "article",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "title": {"type": "string"},
            "publication": {"type": "string"},
            "url": {"type": "string"},
            "summary": {"type": "string"},
            "words": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["topic", "title", "publication", "url", "summary", "words"],
        "additionalProperties": False,
    },
}


def normalize_article(response_json_: Any, topic_: str) -> Article:
    if not isinstance(response_json_, dict) or not isinstance(response_json_.get("summary"), str):
        raise TypeError("the response has no summary")
    summary_ = " ".join(response_json_["summary"].split())
    if not summary_:
        raise ValueError("the summary is empty")
    if len(summary_.split()) > MAX_SUMMARY_WORDS:
        raise ValueError(f"the summary is longer than {MAX_SUMMARY_WORDS} words")
    if not isinstance(response_json_.get("title"), str) or not response_json_["title"].strip():
        raise ValueError("the response has no title")
    words_ = response_json_.get("words") or []
    if not isinstance(words_, list):
        words_ = [words_]
    summary_lower_ = summary_.lower()
    kept_ = [str(word_).strip() for word_ in words_ if str(word_).strip()]
    kept_ = [word_ for word_ in kept_ if word_.lower() in summary_lower_]

    return Article(topic=str(response_json_.get("topic") or topic_).strip().lower(),
                   title=" ".join(response_json_["title"].split()),
                   publication=" ".join(str(response_json_.get("publication") or "").split()),
                   summary=summary_,
                   words=list(dict.fromkeys(kept_))[:MAX_WORDS],
                   url=str(response_json_.get("url") or "").strip())


def read_article(vocabulary_: Vocabulary, topic_: str, cefr_level_: CEFRLevel) -> Article:
    response_ = get_openai_client().responses.create(model=current_model(),
                                                    instructions=read_instructions(vocabulary_, topic_, cefr_level_),
                                                    input="Find the article and write the summary.",
                                                    text={"format": ARTICLE_FORMAT})
    response_json_ = loads(strip_code_fences(response_.output_text))

    return normalize_article(response_json_, topic_)


def check_article(vocabulary_: Vocabulary, topic_: str,
                  cefr_level_: CEFRLevel) -> Tuple[Optional[Article], Optional[str]]:
    try:
        return read_article(vocabulary_, topic_, cefr_level_), None
    except (JSONDecodeError, KeyError, TypeError, ValueError) as error_:
        return None, f"The article could not be read ({type(error_).__name__}: {error_})."
