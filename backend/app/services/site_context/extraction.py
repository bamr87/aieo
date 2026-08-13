"""Phase 2 — deep extraction and metadata analysis for one mapped page.

Phase 1 already fetched (and cached) every body, so nothing here touches the
network except the optional stylesheet fetch, which the service dedupes across
the whole crawl. This module composes three existing pieces into one
:class:`ContextNode`:

* :class:`~app.services.site_snapshot.extractor.PageExtractor` — main-content
  text, headings, tables, lists, links, assets, front-matter-ish metadata and
  the raw-HTML content hash (shared with the audit pipeline);
* :mod:`.presentation` — styles, imagery and motion;
* :mod:`.seo` — the metadata/SEO facts and their defect list.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from ..site_snapshot.discovery import host_key
from ..site_snapshot.extractor import PageExtractor
from ..site_snapshot.model import PageRecord
from . import adapters
from . import presentation as presentation_mod
from . import resources as resources_mod
from . import seo as seo_mod
from .config import ContextConfig
from .link_map import looks_like_index
from .model import ContextNode


class ContextExtractor:
    """Populate a mapped node's content, metadata, presentation and SEO fields."""

    def __init__(self, parser=None):
        self.page_extractor = PageExtractor(parser)

    def extract(
        self,
        node: ContextNode,
        html: str,
        *,
        cfg: ContextConfig,
        css_text: str = "",
        js_text: str = "",
    ) -> ContextNode:
        parts = urlparse(node.url)
        base_url = f"{parts.scheme}://{parts.netloc}/"
        record = PageRecord(
            url=node.url,
            url_key=node.url_key,
            slug=node.slug,
            path=node.path,
            status=node.status,
            discovery_source=node.discovery_source,
            fetched_at=node.fetched_at,
            content_type=node.content_type,
            final_url=node.final_url or node.url,
        )
        try:
            record = self.page_extractor.extract(
                normalized_url=node.url,
                base_url=base_url,
                final_url=node.final_url or node.url,
                html=html,
                content_hash=node.content_hash,
                discovery_source=node.discovery_source,
                root_host=host_key(parts.netloc),
                include_external=cfg.include_external,
                record=record,
                strip_boilerplate=cfg.strip_boilerplate,
                keep_interactive=cfg.keep_interactive,
            )
        except Exception as exc:  # pragma: no cover - defensive
            node.error = (node.error or "") + f" extract: {exc}"
            return node

        node.title = record.title or node.title
        node.description = record.description or node.description
        node.is_index = looks_like_index(
            node.url,
            node.title,
            content_links=len(record.links_internal),
            word_count=record.word_count,
        )

        text = record.text or ""
        if cfg.max_text_chars and len(text) > cfg.max_text_chars:
            text = text[: cfg.max_text_chars]
            truncated = True
        else:
            truncated = False

        # Optional upgrade: a library extractor usually beats the built-in
        # content-root walk on article-shaped pages, and loses badly on hubs
        # (it is built to discard link lists), so the policy is per page.
        engine = "builtin"
        if cfg.use_optional_libraries:
            installed = adapters.available()["trafilatura"]
            if adapters.should_use_library_extractor(
                cfg.extractor, node.is_index, installed
            ):
                upgraded = adapters.extract_main_text(html, node.url)
                # Trust it only when it found more than the built-in path did:
                # a library that returns a stub on an unusual layout must not
                # replace working output.
                if upgraded and upgraded["word_count"] >= record.word_count * 0.9:
                    text = upgraded["text"]
                    record.word_count = upgraded["word_count"]
                    record.char_count = len(text)
                    engine = upgraded["engine"]
                    if cfg.max_text_chars and len(text) > cfg.max_text_chars:
                        text = text[: cfg.max_text_chars]
                        truncated = True

        node.content = {
            "text": text,
            "engine": engine,
            "text_truncated": truncated,
            "summary": record.summary,
            "word_count": record.word_count,
            "char_count": record.char_count,
            "reading_time_min": record.reading_time_min,
            "content_root": record.content_root,
            "headings": record.headers,
            "tables": record.tables[:20],
            "lists": record.lists[:20],
            "is_soft_404": record.is_soft_404,
        }
        node.meta = {
            **(node.meta or {}),
            "lang": record.lang,
            "generator": record.generator,
            "author": record.author,
            "date": record.date,
            "tags": record.tags,
            "categories": record.categories,
            "jsonld_types": record.jsonld_types,
            "open_graph": record.og,
            "canonical": record.canonical or (node.meta or {}).get("canonical"),
        }
        # A link to ellipticcurve.py is a download, not a page to crawl: keep it
        # out of the link graph and put it in the resource inventory instead.
        internal_pages, internal_resources = resources_mod.split_links(
            record.links_internal
        )
        external_pages, external_resources = resources_mod.split_links(
            record.links_external
        )
        node.links = {"internal": internal_pages, "external": external_pages}
        node.assets = (
            record.assets
            + [{**res, "scope": "internal"} for res in internal_resources]
            + [{**res, "scope": "external"} for res in external_resources]
        )
        node.assets += _media_assets(html, node.url)
        node.counts = {
            **(node.counts or {}),
            **record.counts,
            "internal_links": len(internal_pages),
            "external_links": len(external_pages),
            "downloads": len(internal_resources) + len(external_resources),
            "words": record.word_count,
            "headings": len(record.headers),
        }

        if cfg.capture_presentation:
            try:
                node.presentation = presentation_mod.analyze(
                    html, node.url, css_text, js_text
                )
            except Exception as exc:  # pragma: no cover - defensive
                node.presentation = {"error": f"{type(exc).__name__}: {exc}"}

        if cfg.use_optional_libraries:
            extended = adapters.structured_data(html, node.url)
            if extended:
                node.meta["structured_data_syntaxes"] = extended["syntaxes"]
                node.meta["jsonld_types"] = list(
                    dict.fromkeys(record.jsonld_types + extended["types"])
                )
                record.jsonld_types = node.meta["jsonld_types"]

        try:
            node.seo = seo_mod.analyze(record=record, html=html, url=node.url)
        except Exception as exc:  # pragma: no cover - defensive
            node.seo = {"error": f"{type(exc).__name__}: {exc}"}

        node.extracted = True
        return node


def style_rollup(nodes: List[ContextNode]) -> Dict[str, Any]:
    """Site-wide style profile merged from every extracted page."""
    palette: Dict[str, int] = {}
    fonts: Dict[str, int] = {}
    frameworks: Dict[str, int] = {}
    js_frameworks: Dict[str, int] = {}
    breakpoints: Dict[str, int] = {}
    custom_props: Dict[str, str] = {}
    dark_mode = grid = flex = responsive = 0
    analyzed = 0

    for node in nodes:
        styles = (node.presentation or {}).get("styles")
        if not styles:
            continue
        analyzed += 1
        for entry in styles.get("palette", []):
            palette[entry["color"]] = palette.get(entry["color"], 0) + entry["count"]
        for font in styles.get("font_families", []):
            fonts[font] = fonts.get(font, 0) + 1
        for name in styles.get("frameworks", []):
            frameworks[name] = frameworks.get(name, 0) + 1
        for name in ((node.presentation or {}).get("scripts", {}) or {}).get(
            "frameworks", []
        ):
            js_frameworks[name] = js_frameworks.get(name, 0) + 1
        for bp in styles.get("breakpoints", []):
            breakpoints[bp] = breakpoints.get(bp, 0) + 1
        for key, value in (styles.get("custom_properties") or {}).items():
            custom_props.setdefault(key, value)
        dark_mode += bool(styles.get("dark_mode"))
        grid += bool(styles.get("uses_grid"))
        flex += bool(styles.get("uses_flexbox"))
        responsive += bool(styles.get("responsive_meta"))

    return {
        "pages_analyzed": analyzed,
        "palette": [
            {"color": c, "count": n}
            for c, n in sorted(palette.items(), key=lambda kv: -kv[1])[:16]
        ],
        "font_families": [
            f for f, _ in sorted(fonts.items(), key=lambda kv: -kv[1])[:10]
        ],
        "frameworks": sorted(frameworks, key=lambda k: -frameworks[k]),
        "js_frameworks": sorted(js_frameworks, key=lambda k: -js_frameworks[k]),
        "breakpoints": sorted(
            breakpoints,
            key=lambda b: float(
                "".join(ch for ch in b if ch.isdigit() or ch == ".") or 0
            ),
        )[:12],
        "custom_properties": dict(list(custom_props.items())[:40]),
        "dark_mode_pages": dark_mode,
        "grid_pages": grid,
        "flexbox_pages": flex,
        "responsive_meta_pages": responsive,
    }


def animation_rollup(nodes: List[ContextNode]) -> Dict[str, Any]:
    """Site-wide motion profile merged from every extracted page."""
    libraries: Dict[str, int] = {}
    keyframes: Dict[str, int] = {}
    with_motion = reduced_motion = videos = autoplay = canvases = svg_smil = 0
    transitions = animations = 0
    analyzed = 0

    for node in nodes:
        anim = (node.presentation or {}).get("animation")
        if not anim:
            continue
        analyzed += 1
        for lib in anim.get("libraries", []):
            libraries[lib] = libraries.get(lib, 0) + 1
        for name in anim.get("keyframes", []):
            keyframes[name] = keyframes.get(name, 0) + 1
        with_motion += bool(anim.get("has_motion"))
        reduced_motion += bool(anim.get("respects_reduced_motion"))
        transitions += anim.get("transition_declarations", 0)
        animations += anim.get("animation_declarations", 0)
        videos += (anim.get("video", {}) or {}).get("count", 0)
        autoplay += (anim.get("video", {}) or {}).get("autoplay", 0)
        canvases += anim.get("canvas_elements", 0)
        svg_smil += anim.get("svg_smil_elements", 0)

    profile = {
        "pages_analyzed": analyzed,
        "pages_with_motion": with_motion,
        "pages_respecting_reduced_motion": reduced_motion,
        "libraries": sorted(libraries, key=lambda k: -libraries[k]),
        "keyframes": [
            k for k, _ in sorted(keyframes.items(), key=lambda kv: -kv[1])[:24]
        ],
        "animation_declarations": animations,
        "transition_declarations": transitions,
        "videos": videos,
        "autoplay_videos": autoplay,
        "canvas_elements": canvases,
        "svg_smil_elements": svg_smil,
    }
    profile["summary"] = _motion_summary(profile)
    return profile


def _motion_summary(p: Dict[str, Any]) -> str:
    if not p["pages_analyzed"]:
        return "no pages analyzed"
    if not p["pages_with_motion"]:
        return "static site: no CSS animation, motion libraries or media detected"
    bits = [f"{p['pages_with_motion']}/{p['pages_analyzed']} pages show motion"]
    if p["keyframes"]:
        bits.append(f"{len(p['keyframes'])} keyframe animations")
    if p["transition_declarations"]:
        bits.append(f"{p['transition_declarations']} CSS transitions")
    if p["libraries"]:
        bits.append("libraries: " + ", ".join(p["libraries"]))
    if p["pages_with_motion"] and not p["pages_respecting_reduced_motion"]:
        bits.append("no prefers-reduced-motion guard anywhere")
    return "; ".join(bits)


def _media_assets(html: str, page_url: str) -> List[Dict[str, Any]]:
    """Video, audio and embeds — assets the content extractor's img/script scan
    never sees, because they live outside the main-content container or carry
    their source on a child ``<source>``."""
    from urllib.parse import urljoin

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    out: List[Dict[str, Any]] = []
    seen: set = set()

    def add(src, kind, **extra):
        if not src:
            return
        absolute = urljoin(page_url, src)
        if not absolute.lower().startswith(("http://", "https://")) or absolute in seen:
            return
        seen.add(absolute)
        out.append({"url": absolute, "type": kind, **extra})

    for tag in soup.find_all(["video", "audio"]):
        kind = tag.name
        add(tag.get("src"), kind, autoplay=tag.has_attr("autoplay"))
        for source in tag.find_all("source"):
            add(source.get("src"), kind, autoplay=tag.has_attr("autoplay"))
    for tag in soup.find_all("iframe", src=True):
        add(tag.get("src"), "embed", title=tag.get("title"))
    for tag in soup.find_all(["embed", "object"]):
        add(tag.get("src") or tag.get("data"), "embed")
    return out


def interactivity_rollup(nodes: List[ContextNode]) -> Dict[str, Any]:
    """Site-wide inventory of in-page tools — where a visitor can *do* something."""
    pages: List[Dict[str, Any]] = []
    control_types: Dict[str, int] = {}
    total_controls = uploads = sliders = progressive = 0
    analyzed = 0

    for node in nodes:
        inter = (node.presentation or {}).get("interactivity")
        if not inter:
            continue
        analyzed += 1
        if not inter.get("has_interactive_ui"):
            continue
        total_controls += inter.get("controls", 0)
        uploads += inter.get("file_uploads", 0)
        sliders += inter.get("sliders", 0)
        progressive += bool(inter.get("progressive_enhancement"))
        for kind, count in (inter.get("control_types") or {}).items():
            control_types[kind] = control_types.get(kind, 0) + count
        pages.append(
            {
                "url": node.url,
                "title": node.title,
                "controls": inter.get("controls", 0),
                "demo_sections": inter.get("demo_sections", [])[:3],
                "signals": inter.get("signals", [])[:3],
            }
        )

    pages.sort(key=lambda p: -p["controls"])
    return {
        "pages_analyzed": analyzed,
        "interactive_pages": len(pages),
        "total_controls": total_controls,
        "control_types": dict(sorted(control_types.items(), key=lambda kv: -kv[1])),
        "file_upload_pages": uploads,
        "slider_controls": sliders,
        "progressive_enhancement_pages": progressive,
        "pages": pages[:30],
        "summary": (
            f"{len(pages)}/{analyzed} pages carry in-page tools "
            f"({total_controls} controls total)"
            + (f"; {progressive} rely on JS to reveal the demo" if progressive else "")
            if pages
            else "no interactive UI detected on any page"
        ),
    }


def asset_inventory(
    nodes: List[ContextNode], limit: int = 1500
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Deduplicated assets across the crawl, most-referenced first, plus totals.

    The totals are returned separately so a truncated list never reads as "this
    is everything": on a code-heavy site the source downloads alone can fill the
    cap and quietly push every image out of the inventory.
    """
    index: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        for asset in node.assets or []:
            url = asset.get("url")
            if not url:
                continue
            entry = index.setdefault(
                url,
                {
                    "url": url,
                    "type": asset.get("type"),
                    "format": asset.get("format"),
                    "alt": asset.get("alt"),
                    "scope": asset.get("scope"),
                    "ref_count": 0,
                    "pages": [],
                },
            )
            entry["ref_count"] += 1
            if len(entry["pages"]) < 10 and node.url not in entry["pages"]:
                entry["pages"].append(node.url)
    totals: Dict[str, int] = {}
    for entry in index.values():
        kind = entry["type"] or "other"
        totals[kind] = totals.get(kind, 0) + 1
    ranked = sorted(index.values(), key=lambda e: (-e["ref_count"], e["url"]))
    return ranked[:limit], dict(sorted(totals.items(), key=lambda kv: -kv[1]))
