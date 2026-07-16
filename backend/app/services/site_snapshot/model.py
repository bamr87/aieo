"""Canonical in-memory data model for a site snapshot.

Two plain dataclasses every exporter reads from: ``PageRecord`` (one crawled
page) and ``SiteSnapshot`` (the whole-site manifest). ``to_dict`` emits the exact
JSON field names; ``SiteSnapshot.from_dict`` round-trips a saved manifest so any
format can be re-exported offline without re-crawling.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

SNAPSHOT_VERSION = "1"
TOOL_NAME = "aieo-site-snapshot"
GENERATOR = "AIEO SiteSnapshotService 1.0"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(normalized_url: str, base_url: str) -> str:
    """Stable anchor id / export filename from a URL path. Root -> 'index'."""
    path = urlparse(normalized_url).path or "/"
    # Drop a trailing slash and a leading slash before slugging.
    stem = path.strip("/")
    if not stem:
        return "index"
    slug = _SLUG_RE.sub("-", stem.lower()).strip("-")
    return slug or "index"


def reading_time_min(word_count: int, wpm: int = 225) -> float:
    """Estimated reading time in minutes (1 decimal)."""
    if word_count <= 0:
        return 0.0
    return round(word_count / float(wpm), 1)


def domain_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


@dataclass
class PageRecord:
    """One crawled page. ``content_hash`` is over the raw HTML (audit parity);
    ``word_count``/``char_count`` are over the extracted plain text."""

    url: str
    final_url: str = ""
    url_key: str = ""
    slug: str = ""
    path: str = ""
    status: int = 0
    from_cache: bool = False
    stale: bool = False  # served from cache because the live fetch failed
    changed: bool = False
    discovery_source: str = "seed"
    fetched_at: str = ""
    elapsed_ms: int = 0
    content_type: Optional[str] = None
    content_hash: str = ""
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    lang: Optional[str] = None
    canonical: Optional[str] = None
    generator: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    jsonld_types: List[str] = field(default_factory=list)
    og: Dict[str, str] = field(default_factory=dict)
    content_root: str = "body"  # which container the content was extracted from
    word_count: int = 0
    char_count: int = 0
    reading_time_min: float = 0.0
    headers: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    text: str = ""
    markdown: str = ""
    tables: List[Dict[str, Any]] = field(default_factory=list)
    lists: List[Dict[str, Any]] = field(default_factory=list)
    links_internal: List[Dict[str, Any]] = field(default_factory=list)
    links_external: List[Dict[str, Any]] = field(default_factory=list)
    assets: List[Dict[str, Any]] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    truncated: bool = False
    is_soft_404: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageRecord":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class SiteSnapshot:
    """Whole-site manifest. The JSON export is exactly this object."""

    base_url: str
    site_slug: str = ""
    root_host: str = ""
    snapshot_version: str = SNAPSHOT_VERSION
    tool: str = TOOL_NAME
    generator: str = GENERATOR
    site_generator: Optional[str] = None
    is_jekyll: bool = False
    created_at: str = ""
    completed_at: str = ""
    degraded: bool = False
    discovery: Dict[str, Any] = field(default_factory=dict)
    robots: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    totals: Dict[str, Any] = field(default_factory=dict)
    outbound_domains: List[Dict[str, Any]] = field(default_factory=list)
    asset_inventory: List[Dict[str, Any]] = field(default_factory=list)
    link_graph: Dict[str, List[str]] = field(default_factory=dict)
    orphans: List[str] = field(default_factory=list)
    site_summary: str = ""
    errors: List[Dict[str, Any]] = field(default_factory=list)
    pages: List[PageRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["pages"] = [
            p.to_dict() if isinstance(p, PageRecord) else p for p in self.pages
        ]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SiteSnapshot":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        kwargs["pages"] = [PageRecord.from_dict(p) for p in data.get("pages", [])]
        return cls(**kwargs)
