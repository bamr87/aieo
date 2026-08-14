"""Canonical in-memory data model for a site-context dataset.

Two plain dataclasses every exporter reads from: :class:`ContextNode` (one page,
carrying its map position, extracted metadata, presentation profile, SEO facts
and agent analysis) and :class:`SiteContext` (the whole dataset). ``to_dict``
emits the exact JSON field names; ``from_dict`` round-trips a saved manifest so
the dataset can be re-exported offline without re-crawling.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

CONTEXT_VERSION = "1"
TOOL_NAME = "aieo-site-context"
GENERATOR = "AIEO SiteContextService 1.0"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(url: str) -> str:
    """Stable anchor id / filename from a URL path. Root -> 'index'."""
    path = urlparse(url).path or "/"
    stem = path.strip("/")
    if not stem:
        return "index"
    slug = _SLUG_RE.sub("-", stem.lower()).strip("-")
    return slug or "index"


def domain_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


@dataclass
class ContextNode:
    """One page in the context dataset.

    Phase 1 (map) fills the identity/topology fields; phase 2 (extract) fills
    ``content``/``meta``/``seo``/``presentation``; phase 3 (agent) fills
    ``analysis``. ``analysis_method`` records which path produced the analysis:
    ``agent`` (Claude Code CLI over OAuth), ``heuristic`` (deterministic
    fallback) or ``skipped``.
    """

    # ---- identity + topology (phase 1) ----
    url: str
    url_key: str = ""
    slug: str = ""
    path: str = ""
    depth: int = 0
    discovery_source: str = "seed"  # seed | link | sitemap
    parents: List[str] = field(default_factory=list)
    anchor_texts: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    status: int = 0
    final_url: str = ""
    content_type: Optional[str] = None
    content_hash: str = ""
    from_cache: bool = False
    fetched_at: str = ""
    elapsed_ms: int = 0
    error: Optional[str] = None

    # ---- extraction (phase 2) ----
    extracted: bool = False
    title: Optional[str] = None
    description: Optional[str] = None
    is_index: bool = False  # a listing/hub page rather than a leaf article
    content: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    seo: Dict[str, Any] = field(default_factory=dict)
    presentation: Dict[str, Any] = field(default_factory=dict)
    links: Dict[str, Any] = field(default_factory=dict)
    assets: List[Dict[str, Any]] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)

    # ---- agent (phase 3) ----
    analysis: Dict[str, Any] = field(default_factory=dict)
    analysis_method: str = "skipped"
    analysis_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextNode":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class SiteContext:
    """The whole contextual dataset for one seed URL. The JSON export is exactly
    this object."""

    seed_url: str
    base_url: str = ""  # scheme://host/ of the seed
    site_slug: str = ""
    context_key: str = ""
    root_host: str = ""
    context_version: str = CONTEXT_VERSION
    tool: str = TOOL_NAME
    generator: str = GENERATOR
    created_at: str = ""
    completed_at: str = ""
    degraded: bool = False
    config: Dict[str, Any] = field(default_factory=dict)
    robots: Dict[str, Any] = field(default_factory=dict)
    phases: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    totals: Dict[str, Any] = field(default_factory=dict)
    depth_histogram: Dict[str, int] = field(default_factory=dict)
    link_graph: Dict[str, List[str]] = field(default_factory=dict)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    orphans: List[str] = field(default_factory=list)
    hubs: List[Dict[str, Any]] = field(default_factory=list)
    external_references: List[Dict[str, Any]] = field(default_factory=list)
    asset_inventory: List[Dict[str, Any]] = field(default_factory=list)
    style_profile: Dict[str, Any] = field(default_factory=dict)
    animation_profile: Dict[str, Any] = field(default_factory=dict)
    interactivity_profile: Dict[str, Any] = field(default_factory=dict)
    seo_profile: Dict[str, Any] = field(default_factory=dict)
    site_analysis: Dict[str, Any] = field(default_factory=dict)
    analysis_method: str = "skipped"
    errors: List[Dict[str, Any]] = field(default_factory=list)
    nodes: List[ContextNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["nodes"] = [
            n.to_dict() if isinstance(n, ContextNode) else n for n in self.nodes
        ]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SiteContext":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        kwargs["nodes"] = [ContextNode.from_dict(n) for n in data.get("nodes", [])]
        return cls(**kwargs)

    def node_by_url(self, url: str) -> Optional[ContextNode]:
        for node in self.nodes:
            if node.url == url:
                return node
        return None
