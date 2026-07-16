"""SiteSnapshotService — the single public orchestrator for the snapshot feature.

Discovery -> per-URL conditional fetch (through the cache) -> extract -> assemble
a :class:`SiteSnapshot` -> export. No-arg constructible, fully offline, no API
key, runs under the lean ``requirements-ci.txt`` dependency set.
"""

from __future__ import annotations

import base64
import hashlib
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import exporters
from .config import CrawlConfig
from .discovery import (
    USER_AGENT_TOKEN,
    SiteDiscovery,
    host_key,
    in_scope,
    normalize_url,
)
from .extractor import PageExtractor
from .fetcher import Fetcher
from .model import PageRecord, SiteSnapshot, reading_time_min, slugify
from .snapshot_cache import InvalidSlugError, SnapshotCache, site_slug

try:
    from ...core.config import workspace_root
except Exception:  # pragma: no cover

    def workspace_root() -> Path:
        return Path(".aieo-workspace").resolve()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    """Matches ContentParser._hash_content (sha256 of utf-8 bytes)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SiteSnapshotService:
    """Crawl a Jekyll/static site into a cached, offline, multi-format snapshot."""

    def __init__(self, root: Optional[Path] = None, parser=None):
        self.root = Path(root) if root else None
        self.extractor = PageExtractor(parser)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def crawl(self, base_url: str, cfg: Optional[CrawlConfig] = None) -> SiteSnapshot:
        cfg = cfg or CrawlConfig()
        base_url = self._normalize_base(base_url)
        slug = site_slug(base_url)
        root_host = host_key(self._netloc(base_url))
        cache = SnapshotCache(slug, root=self.root)
        if not cfg.use_cache:
            cache.purge()

        site = SiteSnapshot(
            base_url=base_url,
            site_slug=slug,
            root_host=root_host,
            created_at=_now_iso(),
            config=cfg.to_dict(),
        )
        start = time.monotonic()

        with Fetcher(timeout=cfg.timeout, max_bytes=cfg.max_bytes_per_page) as fetcher:
            disc = SiteDiscovery().discover(base_url, fetcher, cache, cfg)
            site.robots = {
                "present": disc.robots_present,
                "sitemaps": disc.sitemap_urls,
                "crawl_delay": disc.crawl_delay,
            }
            delay = max(cfg.delay_seconds, disc.crawl_delay or 0.0)

            pages = self._crawl_frontier(
                base_url, root_host, disc, fetcher, cache, cfg, delay, site
            )

        site.pages = pages
        site.completed_at = _now_iso()
        site.discovery = {
            "sitemap_urls": disc.counts.get("sitemap_urls", 0),
            "feed_urls": disc.counts.get("feed_urls", 0),
            "robots_sitemaps": disc.counts.get("robots_sitemaps", 0),
            "link_followed": sum(1 for p in pages if p.discovery_source == "link"),
            "source": self._provenance(pages),
        }
        self._finalize(site, cfg, start)
        cache.save_manifest(site.to_dict())
        return site

    def export(
        self,
        site: SiteSnapshot,
        formats: List[str],
        out_dir: Path,
        cfg: Optional[CrawlConfig] = None,
    ) -> Dict[str, Dict[str, Any]]:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        assets_map = None
        if cfg and cfg.include_assets and ({"html", "bundle"} & set(formats)):
            assets_map = self._inline_assets(site, cfg)
        results: Dict[str, Dict[str, Any]] = {}
        for fmt in formats:
            if fmt not in exporters.FORMATS:
                results[fmt] = {"error": f"unknown format {fmt!r}"}
                continue
            path = out_dir / f"{site.site_slug}{exporters.extension_for(fmt)}"
            try:
                results[fmt] = exporters.write_export(
                    site, fmt, path, assets_map=assets_map
                )
            except Exception as exc:  # pragma: no cover - defensive
                results[fmt] = {"format": fmt, "error": str(exc)}
        return results

    def snapshot(
        self,
        base_url: str,
        *,
        formats: Optional[List[str]] = None,
        cfg: Optional[CrawlConfig] = None,
        out_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Convenience used by every surface: crawl + export, return a summary dict."""
        cfg = cfg or CrawlConfig()
        formats = formats or ["json", "markdown", "html", "text"]
        site = self.crawl(base_url, cfg)
        if out_dir is None:
            stamp = (
                (site.created_at or _now_iso()).replace(":", "").replace("-", "")[:15]
            )
            base = self.root or workspace_root()
            out_dir = Path(base) / "audits" / "snapshots" / site.site_slug / stamp
        outputs = self.export(site, formats, out_dir, cfg)
        return {
            "base_url": site.base_url,
            "site_slug": site.site_slug,
            "out_dir": str(out_dir),
            "stats": site.stats,
            "discovery": site.discovery,
            "degraded": site.degraded,
            "outputs": outputs,
            "manifest_path": str(
                SnapshotCache(site.site_slug, root=self.root).manifest_path()
            ),
        }

    def load_manifest(self, slug: str) -> Optional[Dict[str, Any]]:
        try:
            return SnapshotCache(slug, root=self.root).load_manifest()
        except InvalidSlugError:
            return None

    def list_snapshots(self) -> List[Dict[str, Any]]:
        base = (self.root or workspace_root()) / ".cache" / "snapshots"
        if not base.exists():
            return []
        out = []
        for d in sorted(base.iterdir()):
            if not d.is_dir():
                continue
            m = SnapshotCache(d.name, root=self.root).load_manifest()
            if m:
                out.append(
                    {
                        "site_slug": d.name,
                        "base_url": m.get("base_url"),
                        "completed_at": m.get("completed_at"),
                        "pages": (m.get("stats") or {}).get("pages_total", 0),
                    }
                )
        return out

    # ------------------------------------------------------------------ #
    # Crawl loop
    # ------------------------------------------------------------------ #
    def _crawl_frontier(
        self, base_url, root_host, disc, fetcher, cache, cfg, delay, site
    ) -> List[PageRecord]:
        # Authoritative seeds (sitemap/feed/home) first, deterministically ordered.
        authoritative = sorted(disc.seeds, key=lambda s: (s[0] != base_url, s[0]))
        queue: deque = deque((url, src, 0) for url, src in authoritative)
        visited: set = set()
        pages: List[PageRecord] = []
        link_pages = 0
        robots_skipped = 0

        while queue and len(visited) < cfg.max_pages:
            url, source, depth = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            if cfg.respect_robots and disc.robots is not None:
                try:
                    if not disc.robots.can_fetch(USER_AGENT_TOKEN, url):
                        robots_skipped += 1
                        continue
                except Exception:
                    pass

            record = self._fetch_one(url, source, fetcher, cache, cfg)
            pages.append(record)
            if delay and not record.from_cache:
                time.sleep(delay)

            # BFS augmentation from internal links (bounded by a separate budget).
            if depth < cfg.max_depth:
                for link in sorted({lnk["url"] for lnk in record.links_internal}):
                    norm = normalize_url(link, base_url)
                    if not norm or norm in visited:
                        continue
                    if not in_scope(norm, root_host, cfg.include_external):
                        continue
                    if self._denied(norm, cfg):
                        continue
                    if link_pages >= cfg.max_link_pages:
                        continue
                    link_pages += 1
                    queue.append((norm, "link", depth + 1))

        site.stats = site.stats or {}
        site.stats["robots_skipped"] = robots_skipped
        site.stats["budget_exhausted"] = bool(queue) and len(visited) >= cfg.max_pages
        return pages

    def _fetch_one(self, url, source, fetcher, cache, cfg) -> PageRecord:
        record = PageRecord(
            url=url,
            url_key=SnapshotCache.url_key(url),
            slug=slugify(url, url),
            path=self._path(url),
            discovery_source=source,
        )
        entry = cache.load(url) if cfg.use_cache else None

        # TTL fast path: reuse without any network (skipped on refresh).
        if (
            entry
            and not cfg.refresh
            and cfg.ttl_seconds > 0
            and SnapshotCache.is_fresh(entry, cfg.ttl_seconds)
        ):
            return self._serve_cached(record, entry, cache, cfg, downloaded=False)

        conditional = None
        if entry and not cfg.refresh:
            conditional = SnapshotCache.conditional_headers(entry)
        result = fetcher.fetch(url, conditional)

        # Network/SSRF error: serve stale if we have a cached copy.
        if result.error:
            if entry:
                rec = self._serve_cached(
                    record, entry, cache, cfg, downloaded=False, stale=True
                )
                rec.error = result.error
                return rec
            record.error = result.error
            record.status = result.status
            return record

        record.status = result.status
        record.final_url = result.final_url
        record.content_type = result.content_type
        record.elapsed_ms = result.elapsed_ms

        # 304 Not Modified: reuse the cached body; refresh the validation timestamp.
        if result.status == 304 and entry:
            new_fetched = _now_iso()
            cache.update_fetched_at(url, new_fetched)
            entry = {**entry, "fetched_at": new_fetched}
            return self._serve_cached(record, entry, cache, cfg, downloaded=False)

        # Non-2xx (404/410/5xx): record the error, do not cache a bad body.
        if not (200 <= result.status < 300):
            record.error = f"HTTP {result.status}"
            return record

        html = result.text
        content_hash = _sha256(html)
        had_prior = entry is not None
        unchanged = had_prior and entry.get("content_hash") == content_hash
        etag = result.headers.get("etag")
        last_modified = result.headers.get("last-modified")
        fetched_at = _now_iso()

        if cfg.use_cache:
            # Truncated bodies ARE cached (with a flag) so re-runs recognize the
            # URL and the capped-byte hash stays stable instead of flapping.
            cache.save(
                url,
                status=result.status,
                content_type=result.content_type,
                text=html,
                content_hash=content_hash,
                fetched_at=fetched_at,
                etag=etag,
                last_modified=last_modified,
                truncated=result.truncated,
            )

        # Re-downloaded but byte-identical: reuse the persisted parse, skip work.
        if unchanged and not cfg.refresh:
            entry = {
                **entry,
                "fetched_at": fetched_at,
                "etag": etag,
                "last_modified": last_modified,
            }
            return self._serve_cached(record, entry, cache, cfg, downloaded=True)

        # changed reflects the real content comparison (even under --refresh,
        # which re-fetches but should still report unchanged content as unchanged).
        record.changed = had_prior and not unchanged
        record.is_new = not had_prior  # transient; read by _finalize, not serialized
        record.truncated = result.truncated
        record.fetched_at = fetched_at
        record.etag = etag
        record.last_modified = last_modified
        populated = self._populate(record, url, html, content_hash, cfg)
        if cfg.use_cache:
            cache.save_record(url, populated.to_dict())
        return populated

    def _serve_cached(
        self, record, entry, cache, cfg, *, downloaded, stale=False
    ) -> PageRecord:
        """Build a record from cache. ``downloaded`` distinguishes a true no-network
        hit (304/TTL/stale) from a re-downloaded-but-unchanged 200 (revalidated)."""
        record.from_cache = not downloaded
        record.revalidated = downloaded and not stale  # transient
        record.stale = stale
        record.changed = False
        record.is_new = False
        record.status = entry.get("status", 200)
        record.content_type = entry.get("content_type")
        record.etag = entry.get("etag")
        record.last_modified = entry.get("last_modified")
        record.fetched_at = entry.get("fetched_at", "")
        record.truncated = bool(entry.get("truncated"))
        record.content_hash = entry.get("content_hash", "")

        persisted = cache.load_record(record.url)
        if persisted:
            return self._rehydrate(record, persisted)
        # Fallback for an older cache with no persisted record: re-parse the body.
        body = cache.read_body(record.url)
        if body is None:
            record.error = (record.error or "") + " cache body unavailable"
            return record
        return self._populate(
            record, record.url, body, entry.get("content_hash", _sha256(body)), cfg
        )

    # Content fields copied verbatim from a persisted record (run-specific fields
    # like status/from_cache/fetched_at are kept from the live record).
    _CONTENT_FIELDS = (
        "title",
        "description",
        "lang",
        "canonical",
        "generator",
        "author",
        "date",
        "tags",
        "categories",
        "jsonld_types",
        "og",
        "content_root",
        "word_count",
        "char_count",
        "reading_time_min",
        "headers",
        "summary",
        "text",
        "markdown",
        "tables",
        "lists",
        "links_internal",
        "links_external",
        "assets",
        "counts",
        "is_soft_404",
        "final_url",
    )

    def _rehydrate(self, record: PageRecord, persisted: dict) -> PageRecord:
        for field_name in self._CONTENT_FIELDS:
            if field_name in persisted:
                setattr(record, field_name, persisted[field_name])
        if not record.final_url:
            record.final_url = record.url
        return record

    def _populate(self, record, url, html, content_hash, cfg) -> PageRecord:
        root_host = host_key(self._netloc(url))
        # Use the snapshot's base for link resolution: the page's own host.
        base_url = f"{self._scheme(url)}://{self._netloc(url)}/"
        try:
            return self.extractor.extract(
                normalized_url=url,
                base_url=base_url,
                final_url=record.final_url or url,
                html=html,
                content_hash=content_hash,
                discovery_source=record.discovery_source,
                root_host=root_host,
                include_external=cfg.include_external,
                record=record,
                strip_boilerplate=cfg.strip_boilerplate,
            )
        except Exception as exc:  # pragma: no cover - defensive
            record.error = (record.error or "") + f" parse: {exc}"
            record.content_hash = content_hash
            return record

    # ------------------------------------------------------------------ #
    # Rollups / finalize
    # ------------------------------------------------------------------ #
    def _finalize(self, site: SiteSnapshot, cfg: CrawlConfig, start: float) -> None:
        pages = site.pages
        ok = [p for p in pages if not p.error]
        errors = [p for p in pages if p.error and not p.stale]
        # from_cache = served WITHOUT a body download (TTL / 304). stale and
        # revalidated (re-downloaded but unchanged) are tracked separately so
        # cache_hit_rate reflects genuine no-network reuse.
        from_cache = [p for p in pages if p.from_cache and not p.stale]
        revalidated = [p for p in pages if getattr(p, "revalidated", False)]
        stale = [p for p in pages if p.stale]
        new = [p for p in pages if getattr(p, "is_new", False) and not p.error]
        changed = [
            p
            for p in pages
            if p.changed and not getattr(p, "is_new", False) and not p.error
        ]

        total = len(pages) or 1
        site.stats.update(
            {
                "pages_total": len(pages),
                "pages_ok": len(ok),
                "pages_from_cache": len(from_cache),
                "pages_revalidated": len(revalidated),
                "pages_stale": len(stale),
                "pages_changed": len(changed),
                "pages_new": len(new),
                "pages_error": len(errors),
                "cache_hit_rate": round(len(from_cache) / total, 3),
                "crawl_seconds": round(time.monotonic() - start, 2),
            }
        )
        site.degraded = (len(stale) / total) > 0.25

        site.errors = [
            {"url": p.url, "error": p.error, "status": p.status}
            for p in pages
            if p.error
        ]

        # Totals.
        total_words = sum(p.word_count for p in pages)
        site.totals = {
            "word_count": total_words,
            "reading_time_min": reading_time_min(total_words),
            "internal_links": sum(p.counts.get("internal_links", 0) for p in pages),
            "external_links": sum(p.counts.get("external_links", 0) for p in pages),
            "images": sum(p.counts.get("images", 0) for p in pages),
            "tables": sum(p.counts.get("tables", 0) for p in pages),
            "lists": sum(p.counts.get("lists", 0) for p in pages),
        }

        # Outbound domains.
        domain_counter: Counter = Counter()
        for p in pages:
            for link in p.links_external:
                if link.get("domain"):
                    domain_counter[link["domain"]] += 1
        site.outbound_domains = [
            {"domain": d, "count": c} for d, c in domain_counter.most_common(100)
        ]

        # Asset inventory.
        asset_map: Dict[str, Dict[str, Any]] = {}
        for p in pages:
            for a in p.assets:
                rec = asset_map.setdefault(
                    a["url"],
                    {"url": a["url"], "type": a["type"], "ref_count": 0, "pages": []},
                )
                rec["ref_count"] += 1
                if p.slug not in rec["pages"]:
                    rec["pages"].append(p.slug)
        site.asset_inventory = sorted(
            asset_map.values(), key=lambda r: (-r["ref_count"], r["url"])
        )[:1000]

        # Link graph + orphans (only edges between crawled pages).
        crawled_slugs = {p.slug for p in pages}
        graph: Dict[str, List[str]] = {}
        targeted: set = set()
        for p in pages:
            targets = []
            for link in p.links_internal:
                t = link.get("target_slug")
                if t and t in crawled_slugs and t != p.slug:
                    targets.append(t)
                    targeted.add(t)
            graph[p.slug] = sorted(set(targets))
        site.link_graph = graph
        home_slug = pages[0].slug if pages else "index"
        site.orphans = sorted(
            s for s in crawled_slugs if s not in targeted and s != home_slug
        )

        # Jekyll detection + site summary.
        home = pages[0] if pages else None
        site.site_generator = home.generator if home else None
        gen = (site.site_generator or "").lower()
        has_feed_and_map = bool(site.discovery.get("feed_urls")) and bool(
            site.discovery.get("sitemap_urls")
        )
        site.is_jekyll = "jekyll" in gen or has_feed_and_map
        if home:
            site.site_summary = home.summary or (home.description or "")

    # ------------------------------------------------------------------ #
    # Asset inlining
    # ------------------------------------------------------------------ #
    def _inline_assets(self, site: SiteSnapshot, cfg: CrawlConfig) -> Dict[str, str]:
        urls: List[str] = []
        seen: set = set()
        for p in site.pages:
            for a in p.assets:
                if a["type"] == "image" and a["url"] not in seen:
                    seen.add(a["url"])
                    urls.append(a["url"])
        urls = urls[: cfg.max_assets]
        out: Dict[str, str] = {}
        if not urls:
            return out
        # Aggregate ceiling so a fleet of max-sized (or decompression-amplified)
        # assets can't blow up memory: cap total inlined bytes.
        budget = cfg.max_assets * cfg.max_asset_bytes
        total = 0
        with Fetcher(timeout=cfg.timeout, max_bytes=cfg.max_asset_bytes) as fetcher:
            for url in urls:
                if total >= budget:
                    break
                data, content_type, err = fetcher.fetch_bytes(url, cfg.max_asset_bytes)
                if err or not data:
                    continue
                total += len(data)
                ctype = (content_type or "image/png").split(";")[0]
                b64 = base64.b64encode(data).decode("ascii")
                out[url] = f"data:{ctype};base64,{b64}"
        return out

    # ------------------------------------------------------------------ #
    # Small URL helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _denied(url: str, cfg: CrawlConfig) -> bool:
        from urllib.parse import urlparse

        path = urlparse(url).path or "/"
        return any(path.startswith(p) for p in cfg.denied_path_prefixes)

    @staticmethod
    def _netloc(url: str) -> str:
        from urllib.parse import urlparse

        return urlparse(url).netloc

    @staticmethod
    def _scheme(url: str) -> str:
        from urllib.parse import urlparse

        return urlparse(url).scheme or "https"

    @staticmethod
    def _path(url: str) -> str:
        from urllib.parse import urlparse

        return urlparse(url).path or "/"

    @staticmethod
    def _provenance(pages: List[PageRecord]) -> str:
        sources = {p.discovery_source for p in pages}
        if sources <= {"seed", "sitemap"}:
            return "sitemap" if "sitemap" in sources else "seed"
        if "link" in sources and "sitemap" in sources:
            return "mixed"
        if "feed" in sources and "sitemap" not in sources:
            return "feed"
        return "mixed" if len(sources) > 1 else next(iter(sources), "seed")

    @staticmethod
    def _normalize_base(base_url: str) -> str:
        base_url = base_url.strip()
        if not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url
        return base_url
