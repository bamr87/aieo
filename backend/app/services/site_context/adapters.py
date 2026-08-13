"""Optional third-party upgrades, each with a working built-in floor.

The repo already uses this shape for PDF export (a pure-stdlib writer that
upgrades to reportlab/Playwright when installed). The same applies here, because
the hard part of reading arbitrary websites is *variability*, and mature
libraries encode years of it:

===================  ===========================================================
``trafilatura``      Main-content extraction. Powers FineWeb/RefinedWeb; the
                     strongest general article extractor available in Python.
``extruct``          Structured data: JSON-LD **plus** Microdata, RDFa and
                     microformats, which a hand-rolled JSON-LD reader misses.
``protego``          robots.txt with modern conventions (wildcards, ``Allow``
                     precedence, per-agent ``Crawl-delay``) — Scrapy's parser.
                     ``urllib.robotparser`` handles the basics only.
===================  ===========================================================

None is required and none is installed by default; each is used only when
importable, and every failure falls back to the built-in path.

**Why extraction is not simply delegated to trafilatura.** Published benchmarks
(WCXB, 2026) put article extraction at F1 ≈ 0.92 for trafilatura but **0.52 on
collections and 0.55 on listings** — and a context build is *seeded* on exactly
those: a category index is nothing but a link list, which article extractors are
designed to discard as boilerplate. So the default is ``auto``: hub/index pages
keep the built-in content-root path, article-shaped pages use trafilatura when
it is installed. ``builtin`` and ``trafilatura`` force one or the other.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

EXTRACTORS = ("auto", "builtin", "trafilatura")


def _try_import(name: str):
    try:
        return __import__(name)
    except Exception:  # pragma: no cover - absence is the normal case
        return None


def available() -> Dict[str, bool]:
    """Which optional upgrades are installed right now."""
    return {
        "trafilatura": _try_import("trafilatura") is not None,
        "extruct": _try_import("extruct") is not None,
        "protego": _try_import("protego") is not None,
    }


# --------------------------------------------------------------------------- #
# Main content
# --------------------------------------------------------------------------- #
def extract_main_text(html: str, url: str = "") -> Optional[Dict[str, Any]]:
    """Main article text via trafilatura, or None when it is unavailable/unsure."""
    module = _try_import("trafilatura")
    if module is None:
        return None
    try:
        text = module.extract(
            html,
            url=url or None,
            include_comments=False,
            include_tables=True,
            include_links=False,
            favor_recall=False,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("trafilatura extraction failed for %s: %s", url, exc)
        return None
    if not text or not text.strip():
        return None
    return {
        "text": text,
        "word_count": len(text.split()),
        "engine": "trafilatura",
    }


def should_use_library_extractor(mode: str, is_index: bool, installed: bool) -> bool:
    """Resolve the ``auto`` policy: library for articles, built-in for hubs."""
    if not installed or mode == "builtin":
        return False
    if mode == "trafilatura":
        return True
    return not is_index  # auto


# --------------------------------------------------------------------------- #
# Structured data
# --------------------------------------------------------------------------- #
def structured_data(html: str, url: str = "") -> Optional[Dict[str, Any]]:
    """JSON-LD + Microdata + RDFa + microformats via extruct, or None."""
    module = _try_import("extruct")
    if module is None:
        return None
    try:
        data = module.extract(html, base_url=url or None, uniform=True)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("extruct failed for %s: %s", url, exc)
        return None
    types: List[str] = []
    for syntax in ("json-ld", "microdata", "rdfa", "microformat"):
        for item in data.get(syntax, []) or []:
            value = item.get("@type") if isinstance(item, dict) else None
            if value:
                types.extend(value if isinstance(value, list) else [value])
    return {
        "engine": "extruct",
        "types": list(dict.fromkeys(str(t) for t in types)),
        "syntaxes": {k: len(v or []) for k, v in data.items()},
    }


# --------------------------------------------------------------------------- #
# robots.txt
# --------------------------------------------------------------------------- #
def robots_parser(text: str, user_agent: str) -> Optional[Tuple[Any, Optional[float]]]:
    """A protego-backed robots parser (``can_fetch``-compatible) plus crawl delay."""
    module = _try_import("protego")
    if module is None:
        return None
    try:
        parsed = module.Protego.parse(text)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("protego failed to parse robots.txt: %s", exc)
        return None

    class _ProtegoAdapter:
        """Presents protego with the urllib.robotparser method names."""

        def __init__(self, inner):
            self._inner = inner

        def can_fetch(self, agent: str, url: str) -> bool:
            return bool(self._inner.can_fetch(url, agent))

        def crawl_delay(self, agent: str):
            return self._inner.crawl_delay(agent)

        def site_maps(self):
            return list(self._inner.sitemaps or [])

    adapter = _ProtegoAdapter(parsed)
    try:
        delay = parsed.crawl_delay(user_agent)
    except Exception:  # pragma: no cover - defensive
        delay = None
    return adapter, (float(delay) if delay else None)
