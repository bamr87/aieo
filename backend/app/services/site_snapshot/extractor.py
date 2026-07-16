"""Turn one fetched HTML page into a :class:`PageRecord`.

Reuses the existing :class:`ContentParser` for text/headers/tables/lists/links
and the raw-HTML content hash (so the snapshot agrees with the audit pipeline),
then layers on snapshot-specific fields: page metadata, Jekyll-flavored front
matter, JSON-LD types, an extractive summary, an internal/external link split,
and an asset inventory.

Contract note (deliberate): ``content_hash`` is over the *raw HTML bytes*, while
``word_count``/``char_count`` are recomputed over the *extracted plain text* —
the two notions of "size" intentionally differ.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from ..content_parser import ContentParser
from .discovery import host_key, normalize_url
from .model import PageRecord, domain_of, reading_time_min, slugify

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_404_RE = re.compile(r"\b(404|page not found|not found|doesn't exist)\b", re.IGNORECASE)
_TOC_LABEL_RE = re.compile(
    r"^\s*(table of contents|contents|on this page|in this article)\s*$", re.IGNORECASE
)


def _anchor(text: str) -> str:
    return _SLUG_RE.sub("-", (text or "").lower()).strip("-")


class PageExtractor:
    def __init__(self, parser: Optional[ContentParser] = None):
        self.parser = parser or ContentParser()

    def extract(
        self,
        *,
        normalized_url: str,
        base_url: str,
        final_url: str,
        html: str,
        content_hash: str,
        discovery_source: str,
        root_host: str,
        include_external: bool,
        record: PageRecord,
        strip_boilerplate: bool = True,
    ) -> PageRecord:
        """Populate ``record`` (already carrying fetch metadata) from ``html``.

        Metadata (title/description/og/jsonld) is read from the whole document,
        but the *content* (text/markdown/headers/links/assets) is read from the
        main-content container with nav/header/footer/modals stripped — so the
        snapshot records each page's UNIQUE content, not the theme's chrome
        repeated on every page. Set ``strip_boilerplate=False`` for full-page
        fidelity.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Metadata from the full document (head) BEFORE any content pruning.
        meta = self._meta(soup)
        record.jsonld_types = self._jsonld_types(soup)
        record.content_root = "body"

        # Choose + clean the content root.
        if strip_boilerplate:
            content_el, root_label = self._select_content_root(soup)
            self._strip_chrome(content_el, drop_landmarks=(root_label == "body"))
            record.content_root = root_label
            content_html = str(content_el)
        else:
            content_html = html

        parsed = self.parser.parse(content_html, format="html")
        content_soup = BeautifulSoup(content_html, "html.parser")

        text = parsed.get("text", "") or ""
        record.content_hash = content_hash
        record.text = text
        record.word_count = len(text.split())
        record.char_count = len(text)
        record.reading_time_min = reading_time_min(record.word_count)
        record.summary = self._summary(soup, text)

        # html2text markdown of the content feeds the markdown/html exports.
        try:
            record.markdown = self.parser.html_converter.handle(content_html)
        except Exception:
            record.markdown = ""

        record.headers = [
            {"level": h["level"], "text": h["text"], "anchor": _anchor(h["text"])}
            for h in parsed.get("headers", [])
        ]
        record.tables = parsed.get("tables", [])
        record.lists = parsed.get("lists", [])

        record.title = meta["title"] or (
            record.headers[0]["text"] if record.headers else None
        )
        record.description = meta["description"]
        record.lang = meta["lang"]
        record.canonical = meta["canonical"]
        record.generator = meta["generator"]
        record.author = meta["author"]
        record.date = meta["date"]
        record.tags = meta["tags"]
        record.categories = meta["categories"]
        record.og = meta["og"]

        internal, external = self._split_links(
            parsed.get("links", []),
            final_url or normalized_url,
            base_url,
            root_host,
            include_external,
        )
        record.links_internal = internal
        record.links_external = external
        record.assets = self._assets(content_soup, final_url or normalized_url)

        record.counts = {
            "tables": len(record.tables),
            "lists": len(record.lists),
            "images": sum(1 for a in record.assets if a["type"] == "image"),
            "internal_links": len(internal),
            "external_links": len(external),
            "code_blocks": len(content_soup.find_all(["pre", "code"])),
        }
        record.is_soft_404 = self._is_soft_404(record)
        return record

    # ---- content-root selection / chrome stripping --------------------

    # Tags that are never page content (always removed).
    _DROP_TAGS = (
        "script",
        "style",
        "noscript",
        "svg",
        "template",
        "form",
        "nav",
        "aside",
    )
    # Structural landmarks dropped only when falling back to <body> (an <article>'s
    # own <header>/<footer> can carry real byline/meta, so they're kept otherwise).
    _LANDMARK_TAGS = ("header", "footer")
    _CHROME_SELECTORS = (
        "[role=dialog]",
        "[role=alertdialog]",
        "[role=navigation]",
        "[role=banner]",
        "[role=contentinfo]",
        "[aria-hidden=true]",
        "[aria-label*='Table of contents' i]",
        ".modal",
        ".offcanvas",
        ".cookie-consent-banner",
        ".navbar",
        ".sidebar",
        ".site-nav",
        ".site-footer",
        ".breadcrumb",
        ".pagination",
        ".toc",
        ".table-of-contents",
        "#toc",
        "#TableOfContents",
        ".skip-link",
    )

    def _select_content_root(self, soup):
        """Return (element, label) for the best main-content container."""
        candidates = [
            ("main", lambda: soup.find("main")),
            ("role=main", lambda: soup.find(attrs={"role": "main"})),
            ("article", lambda: soup.find("article")),
            (
                "#main-content",
                lambda: soup.find(
                    id=re.compile(r"^(main-content|main_content|content|main)$", re.I)
                ),
            ),
            (
                ".content",
                lambda: soup.find(
                    class_=re.compile(
                        r"(page__content|post-content|entry-content|e-content"
                        r"|article-content|markdown-body)",
                        re.I,
                    )
                ),
            ),
        ]
        for label, finder in candidates:
            try:
                el = finder()
            except Exception:
                el = None
            if el and len(el.get_text(strip=True)) > 200:
                return el, label
        return (soup.find("body") or soup), "body"

    def _strip_chrome(self, root, *, drop_landmarks: bool) -> None:
        """Remove non-content elements from the chosen content root in place."""
        if root is None:
            return
        tags = list(self._DROP_TAGS)
        if drop_landmarks:
            tags += list(self._LANDMARK_TAGS)
        for el in root.find_all(tags):
            el.decompose()
        for el in root.select(",".join(self._CHROME_SELECTORS)):
            el.decompose()
        for el in root.find_all(attrs={"hidden": True}):
            el.decompose()
        # Drop orphaned TOC heading labels left behind when the list was a sibling.
        for h in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            if _TOC_LABEL_RE.match(h.get_text(strip=True) or ""):
                h.decompose()

    # ---- helpers -------------------------------------------------------

    def _meta(self, soup) -> Dict[str, Any]:
        def meta_content(**attrs) -> Optional[str]:
            el = soup.find("meta", attrs=attrs)
            if el and el.get("content"):
                return el["content"].strip()
            return None

        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else None

        og: Dict[str, str] = {}
        for el in soup.find_all("meta"):
            prop = el.get("property") or el.get("name") or ""
            if prop.startswith("og:") and el.get("content"):
                og[prop[3:]] = el["content"].strip()

        html_el = soup.find("html")
        lang = html_el.get("lang") if html_el and html_el.get("lang") else None

        canonical_el = soup.find("link", rel="canonical")
        canonical = canonical_el.get("href") if canonical_el else None

        keywords = meta_content(name="keywords")
        tags = [t.strip() for t in keywords.split(",")] if keywords else []
        tags += [
            el["content"].strip()
            for el in soup.find_all("meta", attrs={"property": "article:tag"})
            if el.get("content")
        ]

        return {
            "title": title or meta_content(property="og:title"),
            "description": meta_content(name="description")
            or meta_content(property="og:description"),
            "lang": lang,
            "canonical": canonical,
            "generator": meta_content(name="generator"),
            "author": meta_content(name="author")
            or meta_content(property="article:author"),
            "date": meta_content(property="article:published_time")
            or meta_content(name="date"),
            "tags": list(dict.fromkeys(tags)),
            "categories": [
                el["content"].strip()
                for el in soup.find_all("meta", attrs={"property": "article:section"})
                if el.get("content")
            ],
            "og": og,
        }

    def _jsonld_types(self, soup) -> List[str]:
        types: List[str] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
            except (ValueError, TypeError):
                continue
            blocks = data if isinstance(data, list) else [data]
            for block in blocks:
                if isinstance(block, dict) and "@type" in block:
                    t = block["@type"]
                    types.extend(t if isinstance(t, list) else [t])
        return list(dict.fromkeys(str(t) for t in types))

    def _summary(self, soup, text: str) -> str:
        desc_el = soup.find("meta", attrs={"name": "description"})
        if desc_el and desc_el.get("content"):
            return desc_el["content"].strip()
        sentences = _SENTENCE_RE.split(text.strip())
        return " ".join(sentences[:2]).strip()[:500]

    def _split_links(
        self, links, page_url, base_url, root_host, include_external
    ) -> Tuple[List[Dict], List[Dict]]:
        internal: List[Dict] = []
        external: List[Dict] = []
        seen_int: set = set()
        seen_ext: set = set()
        for link in links:
            href = link.get("url", "")
            text = link.get("text", "")
            if not href or href.startswith(("mailto:", "tel:", "#", "javascript:")):
                continue
            absolute = urljoin(page_url, href)
            parts = urlparse(absolute)
            if parts.scheme not in ("http", "https"):
                continue
            if host_key(parts.netloc) == root_host:
                norm = normalize_url(absolute, base_url)
                if norm and norm not in seen_int:
                    seen_int.add(norm)
                    internal.append(
                        {
                            "url": norm,
                            "text": text,
                            "target_slug": slugify(norm, base_url),
                        }
                    )
            else:
                if absolute not in seen_ext:
                    seen_ext.add(absolute)
                    external.append(
                        {"url": absolute, "text": text, "domain": domain_of(absolute)}
                    )
        return internal, external

    def _assets(self, soup, page_url) -> List[Dict[str, Any]]:
        assets: List[Dict[str, Any]] = []
        seen: set = set()

        def add(src: Optional[str], kind: str, alt: Optional[str] = None) -> None:
            if not src:
                return
            absolute = urljoin(page_url, src)
            if not absolute.lower().startswith(("http://", "https://")):
                return
            if absolute in seen:
                return
            seen.add(absolute)
            assets.append({"url": absolute, "type": kind, "alt": alt})

        for img in soup.find_all("img"):
            add(img.get("src"), "image", img.get("alt"))
        for source in soup.find_all("source"):
            add(source.get("src"), "media")
        for script in soup.find_all("script", src=True):
            add(script.get("src"), "script")
        for link in soup.find_all("link", rel="stylesheet"):
            add(link.get("href"), "style")
        return assets

    def _is_soft_404(self, record: PageRecord) -> bool:
        title = record.title or ""
        if _404_RE.search(title):
            return True
        # A near-empty page whose only heading screams 404.
        if record.word_count < 50 and record.headers:
            return bool(_404_RE.search(record.headers[0]["text"]))
        return False
