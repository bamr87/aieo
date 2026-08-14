"""Phase 2b — the SEO and metadata attributes that can be inferred from a page.

Deterministic and judgement-free by design: this module reports *facts* (what
tags exist, how long they are, what is missing) and flags concrete, uncontested
defects (no ``<h1>``, ``noindex``, a 300-character title). It deliberately emits
no score — per the project's central rule, scoring criteria live in
``backend/prompts/``, and the qualitative read of these facts is the agent's job
in :mod:`.agent`.

Inputs are the already-extracted :class:`PageRecord` (title/description/og/
JSON-LD/headings/links, courtesy of the snapshot extractor) plus the raw HTML
for the head-level tags the record does not carry (twitter cards, hreflang,
viewport, charset, feeds, prev/next, favicon).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

# Widely used display limits; not laws, but the thresholds every SEO tool checks.
TITLE_MIN, TITLE_MAX = 15, 60
DESC_MIN, DESC_MAX = 50, 160
THIN_CONTENT_WORDS = 300

_OG_REQUIRED = ("title", "description", "image", "url", "type")
_TWITTER_REQUIRED = ("card", "title", "description")


def analyze(*, record, html: str, url: str) -> Dict[str, Any]:
    """Return the SEO/metadata dataset for one page, including an issue list."""
    soup = _soup(html)
    head = _head_tags(soup, url) if soup is not None else {}

    title = (record.title or "").strip()
    description = (record.description or "").strip()
    headings = _headings(record.headers or [])
    canonical = (record.canonical or "").strip() or None
    robots_meta = head.get("robots")
    indexable = not bool(robots_meta and re.search(r"\bnoindex\b", robots_meta, re.I))

    og = dict(record.og or {})
    twitter = head.get("twitter", {})
    structured = (
        _structured_data(soup) if soup is not None else {"types": [], "blocks": 0}
    )
    images = _image_facts(soup) if soup is not None else {}

    data: Dict[str, Any] = {
        "title": {
            "text": title or None,
            "length": len(title),
            "status": _length_status(len(title), TITLE_MIN, TITLE_MAX, bool(title)),
        },
        "description": {
            "text": description or None,
            "length": len(description),
            "status": _length_status(
                len(description), DESC_MIN, DESC_MAX, bool(description)
            ),
        },
        "canonical": {
            "href": canonical,
            "self_referential": (
                _same_url(canonical, record.final_url or url) if canonical else None
            ),
        },
        "robots_meta": robots_meta,
        "indexable": indexable,
        "lang": record.lang,
        "charset": head.get("charset"),
        "viewport": head.get("viewport"),
        "hreflang": head.get("hreflang", []),
        "favicon": head.get("favicon"),
        "feeds": head.get("feeds", []),
        "prev_next": head.get("prev_next", {}),
        "amphtml": head.get("amphtml"),
        "open_graph": _completeness(og, _OG_REQUIRED),
        "twitter": _completeness(twitter, _TWITTER_REQUIRED),
        "structured_data": structured,
        "headings": headings,
        "content": {
            "word_count": record.word_count,
            "reading_time_min": record.reading_time_min,
            "thin": record.word_count < THIN_CONTENT_WORDS,
            "content_root": record.content_root,
            "tables": len(record.tables or []),
            "lists": len(record.lists or []),
        },
        "links": {
            "internal": len(record.links_internal or []),
            "external": len(record.links_external or []),
        },
        "images": images,
        "dates": {
            "published": record.date,
            "modified": head.get("modified"),
        },
        "author": record.author,
        "keywords": record.tags or [],
        "categories": record.categories or [],
    }
    data["issues"] = _issues(data, record)
    return data


# --------------------------------------------------------------------------- #
# Head-level tags the PageRecord does not carry
# --------------------------------------------------------------------------- #
def _head_tags(soup, url: str) -> Dict[str, Any]:
    twitter: Dict[str, str] = {}
    for el in soup.find_all("meta"):
        name = (el.get("name") or el.get("property") or "").lower()
        content = (el.get("content") or "").strip()
        if name.startswith("twitter:") and content:
            twitter[name[8:]] = content

    hreflang = [
        {"lang": ln.get("hreflang"), "href": urljoin(url, ln.get("href", ""))}
        for ln in soup.find_all("link", hreflang=True)
    ]
    feeds = [
        {
            "type": ln.get("type"),
            "href": urljoin(url, ln.get("href", "")),
            "title": ln.get("title"),
        }
        for ln in soup.find_all(
            "link", rel=lambda v: v and "alternate" in [r.lower() for r in v]
        )
        if ln.get("type") and "xml" in (ln.get("type") or "")
    ]
    prev_next: Dict[str, str] = {}
    for rel in ("prev", "next"):
        el = soup.find("link", rel=lambda v, r=rel: v and r in [x.lower() for x in v])
        if el and el.get("href"):
            prev_next[rel] = urljoin(url, el["href"])

    favicon = None
    for ln in soup.find_all("link", href=True):
        if any("icon" in r.lower() for r in (ln.get("rel") or [])):
            favicon = urljoin(url, ln["href"])
            break

    amp = soup.find("link", rel=lambda v: v and "amphtml" in [r.lower() for r in v])
    charset_el = soup.find("meta", charset=True)
    viewport_el = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    robots_el = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    modified_el = soup.find(
        "meta", attrs={"property": re.compile(r"^article:modified_time$", re.I)}
    )

    return {
        "twitter": twitter,
        "hreflang": hreflang,
        "feeds": feeds[:5],
        "prev_next": prev_next,
        "favicon": favicon,
        "amphtml": amp.get("href") if amp else None,
        "charset": charset_el.get("charset") if charset_el else None,
        "viewport": viewport_el.get("content") if viewport_el else None,
        "robots": robots_el.get("content") if robots_el else None,
        "modified": modified_el.get("content") if modified_el else None,
    }


def _structured_data(soup) -> Dict[str, Any]:
    """JSON-LD blocks: their @types, plus microdata/RDFa presence."""
    types: List[str] = []
    blocks = 0
    errors: List[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        blocks += 1
        try:
            data = json.loads(script.string or "{}")
        except (ValueError, TypeError) as exc:
            errors.append(f"block {blocks}: invalid JSON ({exc.__class__.__name__})")
            continue
        for block in data if isinstance(data, list) else [data]:
            if isinstance(block, dict):
                graph = block.get("@graph")
                nodes = graph if isinstance(graph, list) else [block]
                for node in nodes:
                    if isinstance(node, dict) and "@type" in node:
                        value = node["@type"]
                        types.extend(value if isinstance(value, list) else [value])
    return {
        "types": list(dict.fromkeys(str(t) for t in types)),
        "blocks": blocks,
        "errors": errors,
        "microdata": bool(soup.find(attrs={"itemscope": True})),
        "rdfa": bool(
            soup.find(attrs={"vocab": True}) or soup.find(attrs={"typeof": True})
        ),
    }


def _image_facts(soup) -> Dict[str, Any]:
    imgs = soup.find_all("img")
    missing = [(img.get("src") or "")[:200] for img in imgs if img.get("alt") is None]
    return {
        "count": len(imgs),
        "missing_alt": len(missing),
        "missing_alt_samples": missing[:5],
    }


def _headings(headers: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    levels: List[int] = []
    for header in headers:
        level = int(header.get("level", 0) or 0)
        if not level:
            continue
        counts[f"h{level}"] = counts.get(f"h{level}", 0) + 1
        levels.append(level)
    skips: List[str] = []
    for prev, curr in zip(levels, levels[1:]):
        if curr - prev > 1:
            skips.append(f"h{prev} -> h{curr}")
    return {
        "counts": counts,
        "h1_count": counts.get("h1", 0),
        "total": len(levels),
        "skips": skips[:10],
        "outline_ok": counts.get("h1", 0) == 1 and not skips,
        "outline": [
            {"level": h.get("level"), "text": h.get("text", "")[:120]}
            for h in headers[:40]
        ],
    }


def _completeness(data: Dict[str, str], required) -> Dict[str, Any]:
    present = [key for key in required if data.get(key)]
    missing = [key for key in required if not data.get(key)]
    return {
        "present": present,
        "missing": missing,
        "complete": not missing,
        "values": {k: v[:200] for k, v in list(data.items())[:12]},
    }


# --------------------------------------------------------------------------- #
# Issues
# --------------------------------------------------------------------------- #
def _issues(data: Dict[str, Any], record) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []

    def add(severity: str, code: str, message: str) -> None:
        out.append({"severity": severity, "code": code, "message": message})

    title = data["title"]
    if title["status"] == "missing":
        add("high", "title_missing", "Page has no <title>.")
    elif title["status"] == "short":
        add("low", "title_short", f"Title is {title['length']} chars (<{TITLE_MIN}).")
    elif title["status"] == "long":
        add(
            "low",
            "title_long",
            f"Title is {title['length']} chars (>{TITLE_MAX}); it will be truncated in results.",
        )

    desc = data["description"]
    if desc["status"] == "missing":
        add(
            "medium",
            "description_missing",
            "No meta description; engines will synthesize one.",
        )
    elif desc["status"] == "short":
        add(
            "low",
            "description_short",
            f"Meta description is {desc['length']} chars (<{DESC_MIN}).",
        )
    elif desc["status"] == "long":
        add(
            "low",
            "description_long",
            f"Meta description is {desc['length']} chars (>{DESC_MAX}).",
        )

    if not data["indexable"]:
        add(
            "high",
            "noindex",
            f"Page is excluded from indexes (robots: {data['robots_meta']}).",
        )
    if not data["canonical"]["href"]:
        add("medium", "canonical_missing", "No rel=canonical link.")
    elif data["canonical"]["self_referential"] is False:
        add(
            "low",
            "canonical_cross",
            f"Canonical points elsewhere: {data['canonical']['href']}",
        )

    headings = data["headings"]
    if headings["h1_count"] == 0:
        add("high", "h1_missing", "Page has no <h1>.")
    elif headings["h1_count"] > 1:
        add("low", "h1_multiple", f"{headings['h1_count']} <h1> elements.")
    if headings["skips"]:
        add(
            "low",
            "heading_skips",
            "Heading levels skip: " + ", ".join(headings["skips"][:3]),
        )

    if not data["viewport"]:
        add("medium", "viewport_missing", "No responsive viewport meta tag.")
    if not data["lang"]:
        add("low", "lang_missing", "No lang attribute on <html>.")

    if data["content"]["thin"]:
        add(
            "medium",
            "thin_content",
            f"Only {data['content']['word_count']} words of main content (<{THIN_CONTENT_WORDS}).",
        )

    if data["images"].get("missing_alt"):
        add(
            "medium",
            "image_alt_missing",
            f"{data['images']['missing_alt']} image(s) have no alt attribute.",
        )

    if not data["structured_data"]["types"]:
        add("medium", "structured_data_missing", "No JSON-LD structured data.")
    if data["structured_data"]["errors"]:
        add(
            "medium",
            "structured_data_invalid",
            "; ".join(data["structured_data"]["errors"][:2]),
        )

    if data["open_graph"]["missing"]:
        add(
            "low",
            "open_graph_incomplete",
            "Missing Open Graph tags: " + ", ".join(data["open_graph"]["missing"]),
        )
    if not data["twitter"]["present"]:
        add("low", "twitter_card_missing", "No Twitter card tags.")

    if data["links"]["internal"] == 0:
        add("medium", "no_internal_links", "Page links to no other page on this site.")

    return out


def rollup(nodes) -> Dict[str, Any]:
    """Site-level SEO facts across every extracted node."""
    extracted = [n for n in nodes if n.extracted and n.seo]
    if not extracted:
        return {"pages_analyzed": 0}

    titles: Dict[str, List[str]] = {}
    descriptions: Dict[str, List[str]] = {}
    issue_counts: Dict[str, int] = {}
    severity_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    schema_types: Dict[str, int] = {}
    missing_canonical: List[str] = []
    noindex: List[str] = []
    thin: List[str] = []

    for node in extracted:
        seo = node.seo
        title = (seo.get("title", {}) or {}).get("text")
        if title:
            titles.setdefault(title, []).append(node.url)
        desc = (seo.get("description", {}) or {}).get("text")
        if desc:
            descriptions.setdefault(desc, []).append(node.url)
        for issue in seo.get("issues", []):
            issue_counts[issue["code"]] = issue_counts.get(issue["code"], 0) + 1
            severity_counts[issue["severity"]] = (
                severity_counts.get(issue["severity"], 0) + 1
            )
        for schema_type in (seo.get("structured_data", {}) or {}).get("types", []):
            schema_types[schema_type] = schema_types.get(schema_type, 0) + 1
        if not (seo.get("canonical", {}) or {}).get("href"):
            missing_canonical.append(node.url)
        if not seo.get("indexable", True):
            noindex.append(node.url)
        if (seo.get("content", {}) or {}).get("thin"):
            thin.append(node.url)

    return {
        "pages_analyzed": len(extracted),
        "issue_counts": dict(sorted(issue_counts.items(), key=lambda kv: -kv[1])),
        "severity_counts": severity_counts,
        "duplicate_titles": [
            {"value": t, "urls": urls} for t, urls in titles.items() if len(urls) > 1
        ][:20],
        "duplicate_descriptions": [
            {"value": d[:120], "urls": urls}
            for d, urls in descriptions.items()
            if len(urls) > 1
        ][:20],
        "schema_types": dict(sorted(schema_types.items(), key=lambda kv: -kv[1])),
        "missing_canonical": missing_canonical[:50],
        "noindex_pages": noindex[:50],
        "thin_pages": thin[:50],
        "avg_word_count": round(
            sum(
                (n.seo.get("content", {}) or {}).get("word_count", 0) for n in extracted
            )
            / len(extracted)
        ),
        "indexable_pages": sum(1 for n in extracted if n.seo.get("indexable", True)),
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _length_status(length: int, low: int, high: int, present: bool) -> str:
    if not present:
        return "missing"
    if length < low:
        return "short"
    if length > high:
        return "long"
    return "ok"


def _same_url(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False

    def key(url: str) -> str:
        parts = urlparse(url)
        host = (parts.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = (parts.path or "/").rstrip("/") or "/"
        return f"{host}{path}"

    return key(a) == key(b)


def _soup(html: str):
    try:
        from bs4 import BeautifulSoup
    except Exception:  # pragma: no cover
        return None
    return BeautifulSoup(html or "", "html.parser")
