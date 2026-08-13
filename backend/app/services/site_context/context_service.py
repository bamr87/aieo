"""SiteContextService — the single public orchestrator for the context feature.

Three phases, in order, each one's output feeding the next:

1. **Map** (:mod:`.link_map`) — walk the seed URL's neighbourhood N levels down,
   recording every link and reference. Bodies land in the shared snapshot cache.
2. **Extract** (:mod:`.extraction`) — for every mapped page, read the cached body
   back (no second request) and derive content, metadata, SEO facts and the
   presentation profile (styles, imagery, animation).
3. **Analyze** (:mod:`.agent`) — loop the pages through the locally
   authenticated Claude Code CLI over OAuth, then one synthesis call that turns
   the per-page records into a site-level picture. Falls back to deterministic
   heuristics when the CLI is unavailable, so the dataset is always complete.

``map_only=True`` stops after phase 1, which is the cheap "just show me the
shape of this section" mode.
"""

from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..site_snapshot.discovery import host_key, normalize_url
from ..site_snapshot.fetcher import Fetcher
from ..site_snapshot.snapshot_cache import SnapshotCache
from . import exporters
from . import presentation as presentation_mod
from .agent import ContextAgent
from .config import ContextConfig
from .extraction import (
    ContextExtractor,
    animation_rollup,
    asset_inventory,
    interactivity_rollup,
    style_rollup,
)
from .link_map import LinkMapper, looks_like_index, render_key
from .model import SiteContext, domain_of
from .renderer import Renderer
from .seo import rollup as seo_rollup
from .store import ContextStore, list_contexts, load_context_manifest

try:
    from ...core.config import workspace_root
except Exception:  # pragma: no cover

    def workspace_root() -> Path:
        return Path(".aieo-workspace").resolve()


_MAX_DISTINCT_STYLESHEETS = 40
_MAX_DISTINCT_SCRIPTS = 40


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SiteContextService:
    """Crawl a URL N levels down into a contextual dataset of the site."""

    def __init__(
        self, root: Optional[Path] = None, parser=None, agent=None, renderer=None
    ):
        self.root = Path(root) if root else None
        self.extractor = ContextExtractor(parser)
        self._agent_override = agent
        # Injectable so tests can exercise the rendered path without a browser.
        self._renderer_override = renderer

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def build(
        self,
        seed_url: str,
        cfg: Optional[ContextConfig] = None,
        *,
        map_only: bool = False,
    ) -> SiteContext:
        cfg = cfg or ContextConfig()
        seed_url = self._normalize_seed(seed_url)
        store = ContextStore(seed_url, root=self.root)
        cache = store.cache
        if not cfg.use_cache:
            # Drops the shared body cache but keeps the context manifest dir alive.
            store.purge()

        ctx = SiteContext(
            seed_url=seed_url,
            base_url=self._base_url(seed_url),
            site_slug=store.site_slug,
            context_key=store.key,
            root_host=host_key(self._netloc(seed_url)),
            created_at=_now_iso(),
            config=cfg.to_dict(),
        )
        start = time.monotonic()
        renderer = self._renderer_override
        if renderer is None and cfg.render:
            renderer = Renderer(
                wait_ms=cfg.render_wait_ms,
                timeout=cfg.timeout,
                wait_until=cfg.render_wait_until,
            )

        try:
            fetcher_cm = Fetcher(timeout=cfg.timeout, max_bytes=cfg.max_bytes_per_page)
            with fetcher_cm as fetcher:
                # ---- phase 1: map the links and references ----
                link_map = LinkMapper(root=self.root, renderer=renderer).map(
                    seed_url, cfg, fetcher, cache
                )
                ctx.nodes = link_map.nodes
                ctx.edges = link_map.edges
                ctx.robots = link_map.robots
                ctx.phases["map"] = link_map.stats
                if renderer is not None:
                    ctx.phases["map"]["render"] = renderer.stats()
                    if not renderer.available():
                        ctx.phases["map"][
                            "render_fallback"
                        ] = renderer.unavailable_reason

                # ---- phase 2: extract + metadata analysis ----
                if map_only:
                    ctx.phases["extract"] = {"skipped": "map_only"}
                else:
                    ctx.phases["extract"] = self._extract_all(
                        ctx, link_map, cache, fetcher, cfg
                    )
        finally:
            if renderer is not None and self._renderer_override is None:
                renderer.close()

        self._finalize_structure(ctx, link_map, cfg)

        # ---- phase 3: the Claude Code agent loop (OAuth) ----
        if map_only or not cfg.agent_enabled:
            ctx.phases["agent"] = {
                "skipped": "map_only" if map_only else "agent disabled by config"
            }
            ctx.analysis_method = "skipped"
        else:
            agent = self._agent_override or ContextAgent(cfg)
            ctx.phases["agent"] = agent.analyze_nodes(ctx.nodes)
            ctx.site_analysis = agent.synthesize(ctx)
            ctx.analysis_method = self._analysis_method(ctx)

        ctx.completed_at = _now_iso()
        ctx.stats["total_seconds"] = round(time.monotonic() - start, 2)
        store.save_manifest(ctx.to_dict())
        return ctx

    def export(
        self, ctx: SiteContext, formats: List[str], out_dir: Path
    ) -> Dict[str, Dict[str, Any]]:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        results: Dict[str, Dict[str, Any]] = {}
        for fmt in formats:
            if fmt not in exporters.FORMATS:
                results[fmt] = {"error": f"unknown format {fmt!r}"}
                continue
            path = out_dir / f"{ctx.context_key}{exporters.extension_for(fmt)}"
            try:
                results[fmt] = exporters.write_export(ctx, fmt, path)
            except Exception as exc:  # pragma: no cover - defensive
                results[fmt] = {"format": fmt, "error": str(exc)}
        return results

    def run(
        self,
        seed_url: str,
        *,
        formats: Optional[List[str]] = None,
        cfg: Optional[ContextConfig] = None,
        out_dir: Optional[Path] = None,
        map_only: bool = False,
    ) -> Dict[str, Any]:
        """Convenience used by every surface: build + export, return a summary."""
        cfg = cfg or ContextConfig()
        formats = formats or ["json", "markdown"]
        ctx = self.build(seed_url, cfg, map_only=map_only)
        if out_dir is None:
            stamp = (
                (ctx.created_at or _now_iso()).replace(":", "").replace("-", "")[:15]
            )
            base = self.root or workspace_root()
            out_dir = Path(base) / "audits" / "context" / ctx.site_slug / stamp
        outputs = self.export(ctx, formats, out_dir)
        analysis = ctx.site_analysis or {}
        return {
            "seed_url": ctx.seed_url,
            "site_slug": ctx.site_slug,
            "context_key": ctx.context_key,
            "out_dir": str(out_dir),
            "stats": ctx.stats,
            "phases": ctx.phases,
            "depth_histogram": ctx.depth_histogram,
            "degraded": ctx.degraded,
            "analysis_method": ctx.analysis_method,
            "context_brief": analysis.get("context_brief"),
            "outputs": outputs,
            "manifest_path": str(
                ContextStore(ctx.seed_url, root=self.root).manifest_path()
            ),
        }

    def load_manifest(
        self, site_slug: str, context_key: str
    ) -> Optional[Dict[str, Any]]:
        return load_context_manifest(site_slug, context_key, root=self.root)

    def list_contexts(self) -> List[Dict[str, Any]]:
        return list_contexts(root=self.root)

    # ------------------------------------------------------------------ #
    # Phase 2
    # ------------------------------------------------------------------ #
    def _extract_all(self, ctx, link_map, cache, fetcher, cfg) -> Dict[str, Any]:
        start = time.monotonic()
        css_cache: Dict[str, str] = {}
        js_cache: Dict[str, str] = {}
        extracted = missing = failed = 0

        for node in ctx.nodes:
            if node.error and not node.content_hash:
                continue
            html = link_map.bodies.get(node.url)
            if html is None and cfg.render:
                html = cache.read_body(render_key(node.url))
            if html is None:
                html = cache.read_body(node.url)
            if html is None:
                if node.status:  # fetched but body not retained (use_cache off)
                    node.error = (node.error or "") + " body unavailable for extraction"
                missing += 1
                continue
            css_text = self._css_for(html, node.url, fetcher, cache, cfg, css_cache)
            js_text = self._js_for(html, node.url, fetcher, cache, cfg, js_cache)
            try:
                self.extractor.extract(
                    node, html, cfg=cfg, css_text=css_text, js_text=js_text
                )
                extracted += 1
            except Exception as exc:  # pragma: no cover - defensive
                node.error = (node.error or "") + f" extract: {exc}"
                failed += 1

        return {
            "extracted": extracted,
            "missing_body": missing,
            "failed": failed,
            "stylesheets_fetched": len(css_cache),
            "scripts_fetched": len(js_cache),
            "extract_seconds": round(time.monotonic() - start, 2),
        }

    def _css_for(self, html, page_url, fetcher, cache, cfg, css_cache) -> str:
        """Fetch (once per URL, site-wide) the page's linked stylesheets."""
        if not cfg.fetch_stylesheets or not cfg.capture_presentation:
            return ""
        urls = presentation_mod.stylesheet_urls(
            html, page_url, limit=cfg.max_stylesheets
        )
        texts: List[str] = []
        for url in urls:
            if url not in css_cache:
                if len(css_cache) >= _MAX_DISTINCT_STYLESHEETS:
                    break
                css_cache[url] = self._fetch_css(url, fetcher, cache, cfg)
            texts.append(css_cache[url])
        return presentation_mod.css_bundle(texts)

    def _js_for(self, html, page_url, fetcher, cache, cfg, js_cache) -> str:
        """Fetch the page's same-host scripts (once per URL, site-wide).

        Third-party scripts (analytics, ads, CDN libraries) are skipped: they are
        huge, they are not this site's behaviour, and their libraries are already
        fingerprinted from the tag's ``src``.
        """
        if not cfg.fetch_scripts or not cfg.capture_presentation:
            return ""
        host = host_key(self._netloc(page_url))
        urls = [
            u
            for u in presentation_mod.script_urls(html, page_url, limit=cfg.max_scripts)
            if host_key(self._netloc(u)) == host
        ]
        texts: List[str] = []
        for url in urls:
            if url not in js_cache:
                if len(js_cache) >= _MAX_DISTINCT_SCRIPTS:
                    break
                js_cache[url] = self._fetch_text_asset(
                    url, fetcher, cache, cfg, cfg.max_script_bytes
                )
            texts.append(js_cache[url])
        return presentation_mod.css_bundle(texts, max_bytes=2 * 1024 * 1024)

    def _fetch_css(self, url, fetcher, cache, cfg) -> str:
        return self._fetch_text_asset(
            url, fetcher, cache, cfg, cfg.max_stylesheet_bytes
        )

    def _fetch_text_asset(self, url, fetcher, cache, cfg, cap) -> str:
        entry = cache.load(url) if (cfg.use_cache and not cfg.refresh) else None
        conditional = SnapshotCache.conditional_headers(entry) if entry else None
        try:
            result = fetcher.fetch(url, conditional)
        except Exception:  # pragma: no cover - fetcher captures its own errors
            return ""
        if result.error or (result.status == 304 and entry):
            return (cache.read_body(url) or "")[:cap]
        if not result.ok:
            return ""
        # Same broken-revalidation guard as the page fetch: a conditional GET
        # answered with an empty "200 OK" must not wipe the cached stylesheet.
        # Losing it is quiet but severe — the whole site's palette, typography
        # and motion profile are read from this one shared file.
        if conditional and not result.text.strip():
            cached = (cache.read_body(url) or "")[:cap]
            if cached.strip():
                return cached
            # Cache holds nothing usable — retry unconditionally to self-heal.
            result = fetcher.fetch(url)
            if not result.ok:
                return ""
        text = result.text[:cap]
        if cfg.use_cache and (text.strip() or not entry):
            cache.save(
                url,
                status=result.status,
                content_type=result.content_type,
                text=text,
                content_hash="",
                fetched_at=_now_iso(),
                etag=result.headers.get("etag"),
                last_modified=result.headers.get("last-modified"),
            )
        return text

    # ------------------------------------------------------------------ #
    # Rollups
    # ------------------------------------------------------------------ #
    def _finalize_structure(self, ctx: SiteContext, link_map, cfg) -> None:
        nodes = ctx.nodes
        known = {n.url for n in nodes}
        extracted = [n for n in nodes if n.extracted]

        # Extraction sets is_index from in-content link density; a map-only run
        # never gets there, so fall back to the path/title signal alone.
        for node in nodes:
            if not node.extracted:
                node.is_index = looks_like_index(node.url, node.title)

        ctx.link_graph = {
            n.url: [c for c in n.children if c in known and c != n.url] for n in nodes
        }
        in_degree: Counter = Counter()
        for source, targets in ctx.link_graph.items():
            for target in targets:
                in_degree[target] += 1

        ctx.hubs = sorted(
            (
                {
                    "url": n.url,
                    "title": n.title,
                    "depth": n.depth,
                    "in_degree": in_degree.get(n.url, 0),
                    "out_degree": len(ctx.link_graph.get(n.url, [])),
                    "is_index": n.is_index,
                }
                for n in nodes
            ),
            key=lambda h: (-h["in_degree"], -h["out_degree"], h["url"]),
        )[:20]
        ctx.orphans = sorted(
            n.url
            for n in nodes
            if n.url != ctx.seed_url and not in_degree.get(n.url) and not n.parents
        )

        histogram: Counter = Counter(str(n.depth) for n in nodes)
        ctx.depth_histogram = dict(sorted(histogram.items(), key=lambda kv: int(kv[0])))

        # External references, rolled up by domain (the per-URL detail stays).
        by_domain: Dict[str, Dict[str, Any]] = {}
        for ref in link_map.external_refs:
            domain = ref.get("domain") or domain_of(ref["url"])
            entry = by_domain.setdefault(
                domain, {"domain": domain, "count": 0, "urls": [], "linked_from": set()}
            )
            entry["count"] += ref.get("count", 1)
            if len(entry["urls"]) < 8:
                entry["urls"].append(ref["url"])
            entry["linked_from"].update(ref.get("from", [])[:5])
        ctx.external_references = [
            {**entry, "linked_from": sorted(entry["linked_from"])[:5]}
            for entry in sorted(
                by_domain.values(), key=lambda e: (-e["count"], e["domain"])
            )
        ][:100]

        ctx.asset_inventory, asset_totals = asset_inventory(nodes)
        ctx.style_profile = style_rollup(extracted)
        ctx.animation_profile = animation_rollup(extracted)
        ctx.interactivity_profile = interactivity_rollup(extracted)
        ctx.seo_profile = seo_rollup(nodes)

        total_words = sum((n.content or {}).get("word_count", 0) for n in extracted)
        ctx.totals = {
            "pages": len(nodes),
            "extracted": len(extracted),
            "word_count": total_words,
            "internal_links": sum(
                len((n.links or {}).get("internal", [])) for n in extracted
            ),
            "external_links": sum(
                len((n.links or {}).get("external", [])) for n in extracted
            ),
            "external_domains": len(ctx.external_references),
            "images": sum(
                ((n.presentation or {}).get("images", {}) or {}).get("count", 0)
                for n in extracted
            ),
            "assets": sum(asset_totals.values()),
            "assets_by_type": asset_totals,
            "downloads": sum(
                n.counts.get("downloads", 0) for n in extracted if n.counts
            ),
            "interactive_pages": (ctx.interactivity_profile or {}).get(
                "interactive_pages", 0
            ),
        }

        errored = [n for n in nodes if n.error]
        ctx.errors = [
            {"url": n.url, "error": n.error, "status": n.status, "depth": n.depth}
            for n in errored
        ][:100]
        ctx.stats = {
            **(link_map.stats or {}),
            "nodes_extracted": len(extracted),
            "nodes_error": len(errored),
            "depth_requested": cfg.depth,
            "scope": cfg.scope,
        }
        ctx.degraded = bool(nodes) and (len(errored) / len(nodes)) > 0.25

    @staticmethod
    def _analysis_method(ctx: SiteContext) -> str:
        methods = {
            n.analysis_method for n in ctx.nodes if n.analysis_method != "skipped"
        }
        if methods == {"agent"}:
            return "agent"
        if "agent" in methods:
            return "mixed"
        return "heuristic" if methods else "skipped"

    # ------------------------------------------------------------------ #
    # URL helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_seed(seed_url: str) -> str:
        url = (seed_url or "").strip()
        if not url:
            raise ValueError("A seed URL is required")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        normalized = normalize_url(url, url)
        if not normalized:
            raise ValueError(f"Not a crawlable page URL: {seed_url!r}")
        return normalized

    @staticmethod
    def _netloc(url: str) -> str:
        from urllib.parse import urlparse

        return urlparse(url).netloc

    @staticmethod
    def _base_url(url: str) -> str:
        from urllib.parse import urlparse

        parts = urlparse(url)
        return f"{parts.scheme}://{parts.netloc}/"
