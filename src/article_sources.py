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
from src.paths import data_root
from src.read_sources import read_sources


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


def retrieve_webpage(url: str, vocabulary: Vocabulary) -> SourceArticle:
    """Fetch public web pages with DNS-pinned connections, including redirects."""
    import http.client
    import certifi
    import ipaddress
    import socket
    import ssl
    from html.parser import HTMLParser

    class TitleParser(HTMLParser):
        def __init__(self):
            super().__init__(); self.in_title = False; self.title = ''
        def handle_starttag(self, tag, attrs):
            if tag.lower() == 'title': self.in_title = True
        def handle_endtag(self, tag):
            if tag.lower() == 'title': self.in_title = False
        def handle_data(self, data):
            if self.in_title: self.title += data

    class PinnedHTTPS(http.client.HTTPSConnection):
        def __init__(self, host, address):
            super().__init__(host, timeout=10, context=ssl.create_default_context(cafile=certifi.where())); self.address = address
        def connect(self):
            sock = socket.create_connection((self.address, 443), self.timeout)
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)

    deadline = time.monotonic() + 35
    try:
        allowed = {source['domain'] for source in read_sources(data_root(), vocabulary.name.lower())}
        for _ in range(4):
            parts = urlsplit(url)
            if parts.scheme != 'https' or not parts.hostname or parts.port not in (None, 443) or parts.username or parts.password:
                raise ArticleRetrievalError('Please enter a public HTTPS article address.')
            hostname = parts.hostname.lower().rstrip('.')
            if not any(hostname == domain or hostname == 'www.' + domain for domain in allowed):
                raise ArticleRetrievalError(f'This website is not an allowed {vocabulary.name.lower()} source. See Allowed sources in the Languages menu.')
            # These publications provide a separately labelled English edition.
            if vocabulary == Vocabulary.FRENCH and hostname in ('lemonde.fr', 'www.lemonde.fr') and parts.path.lower().startswith('/en/'):
                raise ArticleRetrievalError('This is the English edition of Le Monde. Choose a French article.')
            if vocabulary == Vocabulary.GERMAN and hostname in ('spiegel.de', 'www.spiegel.de') and parts.path.lower().startswith('/international/'):
                raise ArticleRetrievalError('This is the international edition of Der Spiegel. Choose a German article.')
            addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                raise ArticleRetrievalError('The article address must point to a public website.')
            if time.monotonic() > deadline: raise ArticleRetrievalError('Article retrieval timed out.')
            connection = PinnedHTTPS(parts.hostname, addresses[0][4][0])
            try:
                path = parts.path or '/'
                if parts.query: path += '?' + parts.query
                connection.request('GET', path, headers={'User-Agent': 'Languages/1.0 (personal reading practice)', 'Accept': 'text/html'})
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader('Location')
                    if not location: raise ArticleRetrievalError('The article redirect has no address.')
                    url = urljoin(url, location)
                    continue
                if response.status in (401, 403):
                    raise ArticleRetrievalError('This website denied access to the article. Please paste the article text instead.')
                if response.status != 200: raise ArticleRetrievalError(f'The website returned HTTP {response.status}.')
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES or time.monotonic() > deadline: raise ArticleRetrievalError('The webpage was too large or too slow.')
            finally:
                connection.close()
            html = data.decode('utf-8', errors='replace')
            if re.search(r'"isAccessibleForFree"\s*:\s*(?:false|"false")', html, re.I):
                raise ArticleRetrievalError('This article appears to be behind a paywall. Try pasting the article text instead.')
            text = extract(html, url=url, include_comments=False, include_tables=False, favor_precision=True)
            if not text or len(text.split()) < 30: raise ArticleRetrievalError('Could not extract enough text from this webpage. Try pasting the article text instead.')
            parser = TitleParser(); parser.feed(html)
            now = datetime.now(timezone.utc).isoformat()
            return SourceArticle(' '.join(parser.title.split()) or 'Article', parts.hostname, url, now, now, text[:24000])
        raise ArticleRetrievalError('Too many redirects.')
    except ArticleRetrievalError:
        raise
    except (OSError, ValueError, http.client.HTTPException, ConfigError) as error:
        raise ArticleRetrievalError('Could not retrieve or read this webpage. Try pasting the article text instead.') from error
