"""Retrieve dated articles from publisher feeds before any model request."""
from configparser import Error as ConfigError
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import re
import time
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

import httpx
from trafilatura import extract

from src.domain import Vocabulary


@dataclass(frozen=True)
class SourceArticle:
    title: str
    publication: str
    url: str
    published_at: str
    retrieved_at: str
    text: str


GUARDIAN = "https://www.theguardian.com"
TAGESSCHAU = "https://www.tagesschau.de"
LEMONDE = "https://www.lemonde.fr"
FEEDS = {
    Vocabulary.ENGLISH: ("The Guardian", GUARDIAN, {
        "finance": "/business/rss", "law": "/law/rss", "physics": "/science/physics/rss",
        "engineering": "/technology/engineering/rss", "politics": "/politics/rss"}),
    Vocabulary.GERMAN: ("tagesschau", TAGESSCHAU, {
        "finance": "/wirtschaft/index~rss2.xml", "law": "/inland/index~rss2.xml",
        "physics": "/wissen/index~rss2.xml", "engineering": "/wissen/index~rss2.xml",
        "politics": "/inland/index~rss2.xml"}),
    Vocabulary.FRENCH: ("Le Monde", LEMONDE, {
        "finance": "/economie/rss_full.xml", "law": "/justice/rss_full.xml",
        "physics": "/physique/rss_full.xml", "engineering": "/industrie/rss_full.xml",
        "politics": "/politique/rss_full.xml"}),
}
GERMAN_FILTERS = {
    "law": r"gericht|justiz|gesetz|recht|urteil|verfass|staatsanwal|prozess",
    "physics": r"physik|quanten|teilchen|universum|atom|energie|fusion|weltraum|astronom|kosmo",
    "engineering": r"technik|technolog|ingenieur|robot|maschine|bau|raket|satellit|chip|energie|reaktor",
}
MAX_BYTES = 2_000_000


class ArticleRetrievalError(ValueError):
    pass


def download(client: httpx.Client, url: str, host: str, deadline: float) -> bytes:
    for _ in range(4):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != host or parsed.port not in (None, 443) or parsed.username:
            raise ArticleRetrievalError("The publisher linked outside its trusted HTTPS site.")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ArticleRetrievalError("Article retrieval timed out.")
        with client.stream("GET", url, timeout=min(8, remaining)) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES or time.monotonic() > deadline:
                    raise ArticleRetrievalError("The publisher response was too large or too slow.")
                chunks.append(chunk)
            return b"".join(chunks)
    raise ArticleRetrievalError("Too many publisher redirects.")


def retrieve_article(vocabulary: Vocabulary, topic: str) -> SourceArticle:
    publication, base, feeds = FEEDS[vocabulary]
    if vocabulary == Vocabulary.FRENCH and topic in ("physics", "engineering"):
        publication, base, feeds = "Sciences et Avenir", "https://www.sciencesetavenir.fr", {
            "physics": "/fondamental/rss.xml", "engineering": "/high-tech/rss.xml"}
    if topic not in feeds:
        raise ArticleRetrievalError("Unknown article topic.")
    now = datetime.now(timezone.utc)
    max_days = 90 if topic in ("physics", "engineering") else 14
    deadline = time.monotonic() + 35
    try:
        with httpx.Client(headers={"User-Agent": "Languages/1.0 (personal reading practice)"},
                          follow_redirects=False) as client:
            feed = ElementTree.fromstring(download(client, base + feeds[topic], urlsplit(base).hostname, deadline))
            candidates = []
            for item in feed.findall("./channel/item"):
                title, url = (item.findtext("title") or "").strip(), (item.findtext("link") or "").strip()
                try:
                    published = parsedate_to_datetime(item.findtext("pubDate") or "")
                    published = published.replace(tzinfo=published.tzinfo or timezone.utc).astimezone(timezone.utc)
                except (TypeError, ValueError, OverflowError):
                    continue
                if not title or not url or not now - timedelta(days=max_days) <= published <= now + timedelta(hours=1):
                    continue
                if vocabulary == Vocabulary.GERMAN and topic in GERMAN_FILTERS:
                    if not re.search(GERMAN_FILTERS[topic], title + " " + (item.findtext("description") or ""), re.I):
                        continue
                candidates.append((published, title, url))
            for published, title, url in sorted(candidates, reverse=True)[:6]:
                try:
                    html = download(client, url, urlsplit(base).hostname, deadline).decode("utf-8", errors="replace")
                    # Do not mistake a subscriber preview for a complete article.
                    if re.search(r'"isAccessibleForFree"\s*:\s*(?:false|"false")', html, re.I):
                        continue
                    try:
                        text = extract(html, url=url, include_comments=False, include_tables=False, favor_precision=True)
                    except (ConfigError, OSError) as error:
                        raise ArticleRetrievalError("Article extraction is unavailable. Please reinstall the app.") from error
                    if not text or len(text.split()) < 120:
                        continue
                    return SourceArticle(title, publication, url, published.isoformat(), now.isoformat(), text[:24000])
                except ArticleRetrievalError as error:
                    if isinstance(error.__cause__, (ConfigError, OSError)):
                        raise
                    continue
                except httpx.HTTPError:
                    continue
    except ArticleRetrievalError as error:
        if isinstance(error.__cause__, (ConfigError, OSError)):
            raise
        raise ArticleRetrievalError(f"Could not retrieve {publication}. Please try again later.") from error
    except (httpx.HTTPError, ElementTree.ParseError) as error:
        raise ArticleRetrievalError(f"Could not retrieve {publication}. Please try again later.") from error
    raise ArticleRetrievalError(
        f"No readable {topic} article from {publication} in the last {max_days} days. Please try another topic or later.")
