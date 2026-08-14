"""Jekyll-tuned, layered URL discovery.

Cheap-first: robots.txt (for the sitemap declaration + crawl rules) ->
sitemap.xml -> feed.xml/atom.xml -> same-domain link BFS as a safety net. All
parsing is standard library (``xml.etree``, ``urllib.robotparser``,
``urllib.parse``); fetching goes through the shared :class:`Fetcher`. Link
extraction prefers BeautifulSoup but falls back to ``html.parser`` so discovery
still works under the lean dependency set.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
from urllib import robotparser
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

from .snapshot_cache import SnapshotCache


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Extensions that are assets, not crawlable HTML pages.
_ASSET_EXT = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|ico|css|js|mjs|json|xml|txt|pdf|zip|gz|tgz|"
    r"mp[34]|m4a|mov|avi|webm|woff2?|ttf|eot|map|rss|atom)$",
    re.IGNORECASE,
)
# Date-archive and pagination traps common in Jekyll themes.
_TRAP_RE = re.compile(r"/(?:19|20)\d{2}/|/page[-/]?\d+/?$|[?&]page=\d+", re.IGNORECASE)


def host_key(netloc: str) -> str:
    """Host comparison key: lowercased, 'www.' stripped, port dropped."""
    netloc = (netloc or "").lower()
    if "@" in netloc:
        netloc = netloc.split("@", 1)[1]
    host = netloc.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_url(url: str, base_url: str) -> Optional[str]:
    """Resolve + canonicalize a URL for identity, or None if not a crawlable page.

    Conservative on purpose: we drop fragments, lowercase scheme/host, drop the
    default port and a trailing ``index.html``, and collapse duplicate slashes —
    but we do NOT force a trailing slash (which would fight server redirects).
    """
    if not url:
        return None
    url = url.strip()
    low = url.lower()
    if low.startswith(("mailto:", "tel:", "javascript:", "data:", "#")):
        return None
    absolute = urljoin(base_url, url)
    absolute, _ = urldefrag(absolute)
    parts = urlparse(absolute)
    if parts.scheme not in ("http", "https"):
        return None
    host = parts.netloc.lower()
    # Strip default ports.
    if host.endswith(":80") and parts.scheme == "http":
        host = host[:-3]
    elif host.endswith(":443") and parts.scheme == "https":
        host = host[:-4]
    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    elif path.endswith("/index.htm"):
        path = path[: -len("index.htm")]
    if _ASSET_EXT.search(path):
        return None
    return urlunparse((parts.scheme, host, path, "", parts.query, ""))


def in_scope(url: str, root_host: str, include_external: bool) -> bool:
    if include_external:
        return True
    return host_key(urlparse(url).netloc) == root_host


class _LinkParser(HTMLParser):
    """stdlib fallback link/asset extractor."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.links.append(value)


def extract_links(html: str) -> List[str]:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        return [a.get("href", "") for a in soup.find_all("a", href=True)]
    except Exception:
        parser = _LinkParser()
        try:
            parser.feed(html)
        except Exception:
            return []
        return parser.links


def _local(tag: str) -> str:
    """Strip XML namespace: '{ns}loc' -> 'loc'."""
    return tag.rsplit("}", 1)[-1]


# Refuse any DTD/entity declaration in fetched XML — stdlib xml.etree on older
# expat is vulnerable to internal-entity ("billion laughs") expansion. Sitemaps
# and feeds never legitimately need a DOCTYPE/ENTITY, so rejecting is safe.
_XML_DECL_RE = re.compile(rb"<!(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)


def safe_xml_parse(text: str):
    """Parse untrusted XML, refusing entity declarations. Returns root or None."""
    data = text.encode("utf-8", "replace")
    if _XML_DECL_RE.search(data):
        return None
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        return None


@dataclass
class Discovery:
    seeds: List[Tuple[str, str]] = field(default_factory=list)  # (url, source)
    robots: Optional[robotparser.RobotFileParser] = None
    robots_present: bool = False
    sitemap_urls: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    crawl_delay: Optional[float] = None


class SiteDiscovery:
    """Discover the URL frontier for a site."""

    def discover(self, base_url, fetcher, cache, cfg) -> Discovery:
        root_host = host_key(urlparse(base_url).netloc)
        robots, declared_sitemaps, present, delay = self.load_robots(
            base_url, fetcher, cache, cfg
        )
        seen: Dict[str, str] = {}  # normalized url -> source (first wins)

        def add(url: str, source: str) -> bool:
            """Return True if the URL is an in-scope page (whether or not new)."""
            norm = normalize_url(url, base_url)
            if not norm or not in_scope(norm, root_host, cfg.include_external):
                return False
            if self._denied(norm, cfg):
                return False
            seen.setdefault(norm, source)
            return True

        # Home page is always the first seed.
        add(base_url, "seed")

        # 2) sitemap(s): declared in robots, else the Jekyll default.
        sitemap_urls = declared_sitemaps or [urljoin(base_url, "/sitemap.xml")]
        sitemap_count = 0
        for loc, _lastmod in self.iter_sitemap_urls(sitemap_urls, fetcher, cache, cfg):
            if add(loc, "sitemap"):
                sitemap_count += 1

        # 3) feed fallback (also augments with recent posts). Count in-scope feed
        # entries regardless of whether the sitemap already had them.
        feed_count = 0
        for loc in self._from_feeds(base_url, fetcher, cache, cfg):
            if add(loc, "feed"):
                feed_count += 1

        disc = Discovery(
            seeds=[(u, s) for u, s in seen.items()],
            robots=robots,
            robots_present=present,
            sitemap_urls=sitemap_urls,
            crawl_delay=delay,
            counts={
                "sitemap_urls": sitemap_count,
                "feed_urls": feed_count,
                "robots_sitemaps": len(declared_sitemaps),
            },
        )
        return disc

    def _denied(self, url: str, cfg) -> bool:
        path = urlparse(url).path or "/"
        if any(path.startswith(p) for p in cfg.denied_path_prefixes):
            return True
        if _TRAP_RE.search(url):
            return True
        return False

    def _cached_fetch(self, url, fetcher, cache, cfg):
        """Fetch a discovery doc (robots/sitemap/feed) with conditional GET so
        re-runs reuse unchanged docs. Returns the body text or None."""
        entry = None
        if cache is not None and cfg.use_cache and not cfg.refresh:
            entry = cache.load(url)
        conditional = SnapshotCache.conditional_headers(entry) if entry else None
        result = fetcher.fetch(url, conditional)
        if result.error:
            if entry:  # serve stale doc rather than losing discovery on a blip
                return cache.read_body(url)
            return None
        if result.status == 304 and entry:
            cache.update_fetched_at(url, _now_iso())
            return cache.read_body(url)
        if result.ok and result.text:
            if cache is not None and cfg.use_cache:
                cache.save(
                    url,
                    status=result.status,
                    content_type=result.content_type,
                    text=result.text,
                    content_hash=_sha256(result.text),
                    fetched_at=_now_iso(),
                    etag=result.headers.get("etag"),
                    last_modified=result.headers.get("last-modified"),
                )
            return result.text
        return None

    def load_robots(self, base_url, fetcher, cache, cfg):
        robots_url = urljoin(base_url, "/robots.txt")
        rp = robotparser.RobotFileParser()
        text = self._cached_fetch(robots_url, fetcher, cache, cfg)
        declared: List[str] = []
        delay: Optional[float] = None
        if text:
            try:
                rp.parse(text.splitlines())
            except Exception:
                rp = robotparser.RobotFileParser()
                rp.allow_all = True
            # Harvest Sitemap: directives (site_maps() exists on 3.8+).
            try:
                maps = rp.site_maps()
                if maps:
                    declared = list(maps)
            except Exception:
                pass
            if not declared:
                for line in text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        declared.append(line.split(":", 1)[1].strip())
            try:
                d = rp.crawl_delay(USER_AGENT_TOKEN)
                if d:
                    delay = float(d)
            except Exception:
                pass
            return rp, declared, True, delay
        rp.allow_all = True
        return rp, declared, False, delay

    def iter_sitemap_urls(
        self, sitemap_urls, fetcher, cache, cfg, _depth=0, _seen=None
    ):
        """Yield (loc, lastmod) handling <urlset> and nested <sitemapindex>."""
        if _seen is None:
            _seen = set()
        if _depth > 3:
            return
        for sm_url in sitemap_urls:
            if sm_url in _seen:
                continue
            _seen.add(sm_url)
            text = self._cached_fetch(sm_url, fetcher, cache, cfg)
            if not text:
                continue
            root = safe_xml_parse(text)
            if root is None:
                continue
            tag = _local(root.tag)
            if tag == "sitemapindex":
                children = [
                    loc.text.strip()
                    for sm in root
                    for loc in sm
                    if _local(loc.tag) == "loc" and loc.text
                ]
                yield from self.iter_sitemap_urls(
                    children, fetcher, cache, cfg, _depth + 1, _seen
                )
            else:  # urlset
                for url_el in root:
                    loc = lastmod = None
                    for child in url_el:
                        name = _local(child.tag)
                        if name == "loc" and child.text:
                            loc = child.text.strip()
                        elif name == "lastmod" and child.text:
                            lastmod = child.text.strip()
                    if loc:
                        yield loc, lastmod

    def _from_feeds(self, base_url, fetcher, cache, cfg) -> List[str]:
        for candidate in ("/feed.xml", "/atom.xml", "/feed/", "/rss.xml"):
            text = self._cached_fetch(urljoin(base_url, candidate), fetcher, cache, cfg)
            if not text:
                continue
            root = safe_xml_parse(text)
            if root is None:
                continue
            urls: List[str] = []
            for el in root.iter():
                name = _local(el.tag)
                if name == "entry":  # Atom
                    for link in el:
                        if _local(link.tag) == "link":
                            href = link.attrib.get("href")
                            rel = link.attrib.get("rel", "alternate")
                            if href and rel == "alternate":
                                urls.append(href)
                elif name == "item":  # RSS
                    for child in el:
                        if _local(child.tag) == "link" and child.text:
                            urls.append(child.text.strip())
            if urls:
                return urls
        return []


# Token used for robots crawl-delay lookups (matches the fetcher UA family).
USER_AGENT_TOKEN = "AIEO-Bot"
