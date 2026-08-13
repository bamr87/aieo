"""Phase 1 — map the links and references before extracting anything.

A context build starts from *any* URL (typically a section/index page such as
``/category/programming``) and walks outward level by level, N levels down. This
phase answers only the structural questions — what pages exist under this seed,
who links to whom, what is referenced off-site — and deliberately does no
content analysis: the deep extraction in :mod:`.extraction` runs afterwards over
the bodies this phase already cached, so nothing is fetched twice.

Differences from the snapshot crawler's discovery, all of them deliberate:

* the **seed is a section, not a site root** — taxonomy prefixes like
  ``/category/`` and ``/page/`` must stay crawlable (a Jekyll-style index's
  items usually live under exactly those prefixes);
* **depth is measured from the seed**, level-ordered, with a per-level budget so
  one huge index cannot starve the deeper levels;
* **scope is selectable** — ``host`` (default), ``domain`` (with subdomains) or
  ``path`` (only URLs under the seed's own path).
"""

from __future__ import annotations

import hashlib
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from ..site_snapshot.discovery import (
    USER_AGENT_TOKEN,
    SiteDiscovery,
    host_key,
    normalize_url,
)
from ..site_snapshot.snapshot_cache import SnapshotCache
from . import adapters
from . import resources as resources_mod
from .config import ContextConfig
from .model import ContextNode, domain_of, slugify

# Pagination frontier traps. Narrower than the snapshot crawler's trap regex on
# purpose: it must not swallow ``/page/<slug>`` item URLs or dated post paths,
# which are exactly the pages a section seed is meant to reach.
_PAGINATION_RE = re.compile(r"/page[-/]?\d+/?$|[?&](?:page|paged)=\d+", re.IGNORECASE)

# A taxonomy landing page: /category/programming, /tag/python — but NOT a post
# that merely lives under one (/blog/my-post), hence the single-segment anchor.
_TAXONOMY_PATH_RE = re.compile(
    r"^/(?:category|categories|tag|tags|topics?|collections?|section)/[^/]+/?$",
    re.IGNORECASE,
)
_INDEX_TAIL_RE = re.compile(
    r"/(?:index|archives?|blog|posts|articles|recent[-_]?pages?)/?$", re.IGNORECASE
)
_INDEX_TITLE_RE = re.compile(
    r"^(?:archives?|index|all\s+\w+|table of contents|listing|directory)\b"
    r"|\b(?:archives?|index)$",
    re.IGNORECASE,
)

# A listing is mostly links with little prose between them. Measured on real
# sites, hubs sit around 4-7 words per in-content link while articles start
# around 10, so 8 separates them with room on both sides.
INDEX_MIN_LINKS = 10
INDEX_MAX_WORDS_PER_LINK = 8

_HTML_TYPES = ("text/html", "application/xhtml")

# Ceiling on bodies held in memory when caching is disabled (phase 2 needs them).
_MEMORY_BODY_BUDGET = 64 * 1024 * 1024


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    """Matches ContentParser._hash_content / the snapshot cache (sha256 of utf-8)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_key(url: str) -> str:
    """Cache identity for a rendered DOM, kept distinct from the served HTML."""
    return f"{url}#__rendered__"


@dataclass
class PageRefs:
    """Everything phase 1 reads off one page."""

    title: Optional[str] = None
    description: Optional[str] = None
    meta_robots: Optional[str] = None
    canonical: Optional[str] = None
    anchors: List[Dict[str, str]] = field(default_factory=list)  # href + text
    asset_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class LinkMap:
    """The phase-1 product: nodes with depth + topology, and the edges between."""

    seed_url: str
    base_url: str
    root_host: str
    nodes: List[ContextNode] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    external_refs: List[Dict[str, Any]] = field(default_factory=list)
    robots: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    # Bodies retained in memory ONLY when the disk cache is off, so phase 2 can
    # still extract without a second request. Bounded by _MEMORY_BODY_BUDGET.
    bodies: Dict[str, str] = field(default_factory=dict)

    def node_map(self) -> "OrderedDict[str, ContextNode]":
        return OrderedDict((n.url, n) for n in self.nodes)


def in_scope(url: str, seed_url: str, root_host: str, cfg: ContextConfig) -> bool:
    """Is ``url`` inside the configured crawl scope for this seed?"""
    if cfg.include_external:
        return True
    parts = urlparse(url)
    hk = host_key(parts.netloc)
    if cfg.scope == "domain":
        if not (hk == root_host or hk.endswith("." + root_host)):
            return False
    elif hk != root_host:
        return False
    if cfg.scope == "path":
        seed_prefix = (urlparse(seed_url).path or "/").rstrip("/")
        path = parts.path or "/"
        if seed_prefix and not (
            path == seed_prefix or path.startswith(seed_prefix + "/")
        ):
            return False
    return True


def is_denied(url: str, cfg: ContextConfig) -> bool:
    path = urlparse(url).path or "/"
    if any(path.startswith(p) for p in cfg.denied_path_prefixes):
        return True
    if cfg.skip_pagination and _PAGINATION_RE.search(url):
        return True
    # Downloads (source files, archives, media) are resources to record, not
    # pages to fetch — crawling them costs a request and yields "not HTML".
    if resources_mod.is_resource(url):
        return True
    return False


def looks_like_index(
    url: str,
    title: Optional[str] = None,
    content_links: int = 0,
    word_count: int = 0,
) -> bool:
    """Heuristic: is this a listing/hub page rather than a leaf article?

    ``content_links`` must be the count of links in the page's *main content*
    (chrome stripped), never the raw anchor count — a leaf article surrounded by
    a 20-link site nav is not a hub, and counting nav links flagged one in three
    real pages as an index.
    """
    path = urlparse(url).path or "/"
    if path in ("", "/"):
        return True
    if _TAXONOMY_PATH_RE.match(path) or _INDEX_TAIL_RE.search(path):
        return True
    if title and _INDEX_TITLE_RE.search(title.strip()):
        return True
    if content_links >= INDEX_MIN_LINKS:
        return (word_count / content_links) <= INDEX_MAX_WORDS_PER_LINK
    return False


class LinkMapper:
    """Walk the seed's neighbourhood N levels down, recording links + references."""

    def __init__(self, root=None, renderer=None):
        self.root = root
        # When set (and usable), pages are read from the post-JavaScript DOM.
        self.renderer = renderer

    # ------------------------------------------------------------------ #
    def map(
        self,
        seed_url: str,
        cfg: ContextConfig,
        fetcher,
        cache: SnapshotCache,
    ) -> LinkMap:
        start = time.monotonic()
        parts = urlparse(seed_url)
        base_url = f"{parts.scheme}://{parts.netloc}/"
        root_host = host_key(parts.netloc)
        lm = LinkMap(seed_url=seed_url, base_url=base_url, root_host=root_host)

        robots, robots_present, crawl_delay = self._robots(
            base_url, fetcher, cache, cfg
        )
        lm.robots = {
            "present": robots_present,
            "crawl_delay": crawl_delay,
            "respected": cfg.respect_robots,
        }
        delay = max(cfg.delay_seconds, crawl_delay or 0.0)

        nodes: "OrderedDict[str, ContextNode]" = OrderedDict()
        seed_node = ContextNode(
            url=seed_url,
            url_key=SnapshotCache.url_key(seed_url),
            slug=slugify(seed_url),
            path=parts.path or "/",
            depth=0,
            discovery_source="seed",
        )
        nodes[seed_url] = seed_node

        level: List[str] = [seed_url]
        depth = 0
        robots_skipped = 0
        unfollowed = 0
        deferred = 0
        retained = 0
        external_seen: Dict[str, Dict[str, Any]] = {}

        while level and depth <= cfg.depth and len(nodes) <= cfg.max_pages:
            next_level: List[str] = []
            for url in level:
                node = nodes[url]
                if (
                    cfg.respect_robots
                    and robots is not None
                    and not self._allowed(robots, url)
                ):
                    node.error = "blocked by robots.txt"
                    robots_skipped += 1
                    continue

                html, fetch_meta = self._fetch(url, fetcher, cache, cfg)
                self._stamp(node, fetch_meta)
                if delay and not fetch_meta.get("from_cache"):
                    time.sleep(delay)
                if html is None:
                    continue
                if not cfg.use_cache and retained + len(html) <= _MEMORY_BODY_BUDGET:
                    lm.bodies[url] = html
                    retained += len(html)

                refs = parse_refs(html, node.final_url or url)
                node.title = refs.title
                node.description = refs.description
                node.counts = dict(refs.asset_counts)
                if refs.canonical:
                    node.meta["canonical"] = urljoin(
                        node.final_url or url, refs.canonical
                    )
                if refs.meta_robots:
                    node.meta["robots"] = refs.meta_robots

                internal, external = self._classify(
                    refs.anchors, node.final_url or url, seed_url, root_host, cfg
                )
                node.counts["internal_links"] = len(internal)
                node.counts["external_links"] = len(external)

                for ref in external:
                    key = ref["url"]
                    entry = external_seen.setdefault(
                        key,
                        {
                            "url": key,
                            "domain": ref["domain"],
                            "count": 0,
                            "texts": [],
                            "from": [],
                        },
                    )
                    entry["count"] += 1
                    if ref["text"] and ref["text"] not in entry["texts"]:
                        entry["texts"].append(ref["text"][:120])
                    if url not in entry["from"]:
                        entry["from"].append(url)

                for target, text in internal:
                    lm.edges.append(
                        {"source": url, "target": target, "text": text[:160]}
                    )
                    existing = nodes.get(target)
                    if existing is not None:
                        if url not in existing.parents and target != url:
                            existing.parents.append(url)
                        if text and text not in existing.anchor_texts:
                            existing.anchor_texts.append(text[:160])
                        if target not in node.children and target != url:
                            node.children.append(target)
                        continue
                    if depth >= cfg.depth:
                        deferred += 1
                        continue
                    if len(nodes) >= cfg.max_pages:
                        deferred += 1
                        continue
                    if len(next_level) >= cfg.max_pages_per_level:
                        deferred += 1
                        continue
                    child = ContextNode(
                        url=target,
                        url_key=SnapshotCache.url_key(target),
                        slug=slugify(target),
                        path=urlparse(target).path or "/",
                        depth=depth + 1,
                        discovery_source="link",
                        parents=[url],
                        anchor_texts=[text[:160]] if text else [],
                    )
                    nodes[target] = child
                    next_level.append(target)
                    if target not in node.children:
                        node.children.append(target)

                unfollowed += len(refs.anchors) - len(internal) - len(external)

            # Optionally top up level 1 from the sitemap (pages an index paginates
            # away, or that are only reachable through a search box).
            if depth == 0 and cfg.follow_sitemap:
                added = self._augment_from_sitemap(
                    lm,
                    nodes,
                    next_level,
                    seed_url,
                    base_url,
                    root_host,
                    cfg,
                    fetcher,
                    cache,
                )
                lm.stats["sitemap_added"] = added

            level = next_level
            depth += 1

        lm.nodes = list(nodes.values())
        lm.external_refs = sorted(
            external_seen.values(), key=lambda r: (-r["count"], r["url"])
        )[:500]

        crawled = [n for n in lm.nodes if n.status or n.error]
        lm.stats.update(
            {
                "nodes_total": len(lm.nodes),
                "nodes_fetched": len([n for n in crawled if not n.error]),
                "nodes_error": len([n for n in lm.nodes if n.error]),
                "nodes_pending": len(lm.nodes) - len(crawled),
                "edges": len(lm.edges),
                "external_refs": len(lm.external_refs),
                "levels_walked": depth,
                "max_depth_reached": max((n.depth for n in lm.nodes), default=0),
                "robots_skipped": robots_skipped,
                "unfollowed_links": max(unfollowed, 0),
                "deferred_links": deferred,
                "budget_exhausted": len(nodes) >= cfg.max_pages,
                "bodies_in_memory": len(lm.bodies),
                "map_seconds": round(time.monotonic() - start, 2),
            }
        )
        return lm

    # ------------------------------------------------------------------ #
    # Fetch (conditional GET through the shared snapshot cache)
    # ------------------------------------------------------------------ #
    def _fetch(
        self, url: str, fetcher, cache: SnapshotCache, cfg: ContextConfig
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Return (html, meta). ``html`` is None when the page is unusable."""
        if self.renderer is not None and self.renderer.available():
            return self._render(url, cache, cfg)
        meta: Dict[str, Any] = {"url": url, "from_cache": False}
        entry = cache.load(url) if cfg.use_cache else None

        if (
            entry
            and not cfg.refresh
            and cfg.ttl_seconds > 0
            and SnapshotCache.is_fresh(entry, cfg.ttl_seconds)
        ):
            body = cache.read_body(url)
            if body is not None:
                meta.update(self._cached_meta(entry), from_cache=True)
                return body, meta

        conditional = (
            SnapshotCache.conditional_headers(entry)
            if entry and not cfg.refresh
            else None
        )
        result = fetcher.fetch(url, conditional)

        if result.error:
            if entry:
                body = cache.read_body(url)
                if body is not None:
                    meta.update(self._cached_meta(entry), from_cache=True, stale=True)
                    meta["error"] = result.error
                    return body, meta
            meta.update(status=result.status, error=result.error)
            return None, meta

        meta.update(
            status=result.status,
            final_url=result.final_url,
            content_type=result.content_type,
            elapsed_ms=result.elapsed_ms,
        )

        if result.status == 304 and entry:
            fetched_at = _now_iso()
            cache.update_fetched_at(url, fetched_at)
            body = cache.read_body(url)
            if body is not None:
                meta.update(self._cached_meta({**entry, "fetched_at": fetched_at}))
                meta["from_cache"] = True
                meta["status"] = 304
                return body, meta

        if not (200 <= result.status < 300):
            meta["error"] = f"HTTP {result.status}"
            return None, meta

        # Broken revalidation: some servers (nginx setups that mishandle
        # If-None-Match) answer a conditional GET with "200 OK" and an EMPTY
        # body instead of "304 Not Modified". Taken at face value that would
        # overwrite a good cached page with nothing and silently empty the
        # dataset on every re-run, so treat it as the 304 it meant to be.
        if conditional and not result.text.strip():
            cached = cache.read_body(url) if entry else None
            if cached:
                fetched_at = _now_iso()
                cache.update_fetched_at(url, fetched_at)
                meta.update(self._cached_meta({**entry, "fetched_at": fetched_at}))
                meta["from_cache"] = True
                meta["revalidated_empty"] = True
                return cached, meta
            # No usable cached copy (e.g. an earlier run already stored the
            # empty response): retry unconditionally so the cache self-heals.
            result = fetcher.fetch(url)
            meta.update(
                status=result.status,
                final_url=result.final_url,
                content_type=result.content_type,
                elapsed_ms=result.elapsed_ms,
                repaired=True,
            )
            if result.error or not (200 <= result.status < 300):
                meta["error"] = result.error or f"HTTP {result.status}"
                return None, meta

        ctype = (result.content_type or "").lower()
        if ctype and not any(t in ctype for t in _HTML_TYPES):
            meta["error"] = f"not HTML ({ctype.split(';')[0]})"
            return None, meta

        html = result.text
        content_hash = _sha256(html)
        meta.update(content_hash=content_hash, fetched_at=_now_iso())
        if cfg.use_cache and (html.strip() or not entry):
            cache.save(
                url,
                status=result.status,
                content_type=result.content_type,
                text=html,
                content_hash=content_hash,
                fetched_at=meta["fetched_at"],
                etag=result.headers.get("etag"),
                last_modified=result.headers.get("last-modified"),
                truncated=result.truncated,
            )
        return html, meta

    def _render(self, url, cache: SnapshotCache, cfg: ContextConfig):
        """Read a page through the headless browser.

        Rendered runs are not incremental: a DOM has no ETag, so every page is
        rendered fresh. The result is still cached (under a render-scoped key,
        so it never collides with the statically fetched body) which keeps
        re-exports offline and lets phase 2 read it back without re-rendering.
        """
        meta: Dict[str, Any] = {"url": url, "from_cache": False, "rendered": True}
        result = self.renderer.render(url)
        meta.update(
            status=result.status,
            final_url=result.final_url,
            content_type="text/html",
            elapsed_ms=result.elapsed_ms,
        )
        if result.error or not result.html.strip():
            cached = cache.read_body(render_key(url))
            if cached:
                meta["from_cache"] = True
                meta["stale"] = True
                meta["error"] = result.error
                return cached, meta
            meta["error"] = result.error or "renderer returned an empty document"
            return None, meta

        html = result.html
        meta.update(content_hash=_sha256(html), fetched_at=_now_iso())
        if cfg.use_cache:
            cache.save(
                render_key(url),
                status=result.status or 200,
                content_type="text/html",
                text=html,
                content_hash=meta["content_hash"],
                fetched_at=meta["fetched_at"],
                etag=None,
                last_modified=None,
            )
        return html, meta

    @staticmethod
    def _cached_meta(entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": entry.get("status", 200),
            "content_type": entry.get("content_type"),
            "content_hash": entry.get("content_hash", ""),
            "fetched_at": entry.get("fetched_at", ""),
        }

    @staticmethod
    def _stamp(node: ContextNode, meta: Dict[str, Any]) -> None:
        node.status = meta.get("status", node.status)
        node.final_url = meta.get("final_url") or node.final_url or node.url
        node.content_type = meta.get("content_type")
        node.content_hash = meta.get("content_hash", "")
        node.from_cache = bool(meta.get("from_cache"))
        node.fetched_at = meta.get("fetched_at", "")
        node.elapsed_ms = int(meta.get("elapsed_ms", 0) or 0)
        if meta.get("error"):
            node.error = meta["error"]

    # ------------------------------------------------------------------ #
    def _classify(
        self, anchors, page_url: str, seed_url: str, root_host: str, cfg: ContextConfig
    ) -> Tuple[List[Tuple[str, str]], List[Dict[str, str]]]:
        """Split a page's anchors into crawlable in-scope targets and off-scope refs."""
        internal: List[Tuple[str, str]] = []
        external: List[Dict[str, str]] = []
        seen_int: set = set()
        seen_ext: set = set()
        for anchor in anchors:
            href = anchor.get("href", "")
            text = (anchor.get("text") or "").strip()
            if not href:
                continue
            absolute = urljoin(page_url, href)
            if not absolute.lower().startswith(("http://", "https://")):
                continue
            if in_scope(absolute, seed_url, root_host, cfg):
                norm = normalize_url(absolute, page_url)
                if not norm or is_denied(norm, cfg) or norm in seen_int:
                    continue
                seen_int.add(norm)
                internal.append((norm, text))
            else:
                if absolute in seen_ext:
                    continue
                seen_ext.add(absolute)
                external.append(
                    {"url": absolute, "text": text, "domain": domain_of(absolute)}
                )
        return internal, external

    def _augment_from_sitemap(
        self, lm, nodes, next_level, seed_url, base_url, root_host, cfg, fetcher, cache
    ) -> int:
        """Add in-scope sitemap URLs as level-1 nodes (bounded by the level budget)."""
        added = 0
        discovery = SiteDiscovery()
        sitemaps = [urljoin(base_url, "/sitemap.xml")]
        try:
            for loc, _lastmod in discovery.iter_sitemap_urls(
                sitemaps, fetcher, cache, cfg
            ):
                if (
                    len(nodes) >= cfg.max_pages
                    or len(next_level) >= cfg.max_pages_per_level
                ):
                    break
                norm = normalize_url(loc, base_url)
                if not norm or norm in nodes:
                    continue
                if not in_scope(norm, seed_url, root_host, cfg) or is_denied(norm, cfg):
                    continue
                nodes[norm] = ContextNode(
                    url=norm,
                    url_key=SnapshotCache.url_key(norm),
                    slug=slugify(norm),
                    path=urlparse(norm).path or "/",
                    depth=1,
                    discovery_source="sitemap",
                    parents=[seed_url],
                )
                next_level.append(norm)
                added += 1
        except Exception:  # pragma: no cover - a missing sitemap is not fatal
            return added
        return added

    def _robots(self, base_url, fetcher, cache, cfg):
        try:
            discovery = SiteDiscovery()
            robots, _declared, present, delay = discovery.load_robots(
                base_url, fetcher, cache, cfg
            )
            # protego understands wildcards and Allow precedence, which
            # urllib.robotparser does not; use it when it is installed.
            if present and cfg.use_optional_libraries:
                text = discovery._cached_fetch(
                    urljoin(base_url, "/robots.txt"), fetcher, cache, cfg
                )
                upgraded = adapters.robots_parser(text or "", USER_AGENT_TOKEN)
                if upgraded:
                    robots, protego_delay = upgraded
                    delay = protego_delay or delay
            return robots, present, delay
        except Exception:  # pragma: no cover - robots must never break a crawl
            return None, False, None

    @staticmethod
    def _allowed(robots, url: str) -> bool:
        try:
            return bool(robots.can_fetch(USER_AGENT_TOKEN, url))
        except Exception:
            return True


# --------------------------------------------------------------------------- #
# Reference parsing
# --------------------------------------------------------------------------- #
def parse_refs(html: str, page_url: str) -> PageRefs:
    """Read a page's links + reference counts. Cheap: no content extraction."""
    refs = PageRefs()
    try:
        from bs4 import BeautifulSoup
    except Exception:  # pragma: no cover - bs4 is in the lean dependency set
        return refs

    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.find("title")
    refs.title = title_el.get_text(strip=True) if title_el else None
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        refs.description = desc["content"].strip()
    robots_el = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    if robots_el and robots_el.get("content"):
        refs.meta_robots = robots_el["content"].strip()
    canonical_el = soup.find("link", rel="canonical")
    if canonical_el and canonical_el.get("href"):
        refs.canonical = canonical_el["href"].strip()

    for a in soup.find_all("a", href=True):
        refs.anchors.append(
            {"href": a["href"], "text": a.get_text(" ", strip=True)[:200]}
        )

    refs.asset_counts = {
        "images": len(soup.find_all("img")),
        "scripts": len(soup.find_all("script", src=True)),
        "stylesheets": len(soup.find_all("link", rel="stylesheet")),
        "media": len(soup.find_all(["video", "audio", "source"])),
        "iframes": len(soup.find_all("iframe")),
    }
    return refs
