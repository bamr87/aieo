"""Phase 3 — loop every mapped page through a Claude Code agent over OAuth.

The agent is the locally authenticated **Claude Code CLI**, driven through
:mod:`app.services.claude_cli` (``claude -p --output-format json``). That means
no ``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` is involved: the CLI carries its
own OAuth credentials, exactly like the ``claude-cli`` scoring provider.

The loop is bounded on every axis that can cost money or time:

* only ``agent_max_pages`` pages get a call, chosen by importance (the seed
  first, then hubs and substantial pages, shallowest first);
* calls run concurrently with ``agent_concurrency`` workers;
* a circuit breaker trips after three consecutive failures, so an expired login
  or an offline machine costs three timeouts, not twenty-five;
* every page the agent does not (or cannot) analyze still gets a deterministic
  heuristic analysis, so the dataset is never partially empty — ``analysis_method``
  on each node records which path produced it.

The instructions themselves are markdown, not Python: ``prompts/agents/
site-context-analyst.md`` (per page) and ``site-context-synthesizer.md``
(site-level), following the repo rule that prompt-shaped logic lives in
``backend/prompts/``.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Sequence

from .config import ContextConfig
from .model import ContextNode

logger = logging.getLogger(__name__)

ANALYST_AGENT = "site-context-analyst"
SYNTHESIZER_AGENT = "site-context-synthesizer"
_MAX_CONSECUTIVE_FAILURES = 3

_FALLBACK_ANALYST_PROMPT = (
    "You analyze one page of a website and return a JSON object describing its "
    "context: page_type, topics, entities, audience, summary, key_points, "
    "seo_assessment, design_notes, relationships and confidence. Return JSON only."
)
_FALLBACK_SYNTHESIS_PROMPT = (
    "You synthesize a whole-site contextual dataset from per-page analyses and a "
    "link map. Return JSON only."
)


class ContextAgent:
    """Runs the per-page and site-level analysis passes through Claude Code."""

    def __init__(
        self,
        cfg: ContextConfig,
        *,
        prompt_loader=None,
        runner: Optional[Callable[..., str]] = None,
    ):
        self.cfg = cfg
        self._runner = runner
        self._prompt_loader = prompt_loader
        self._prompts: Dict[str, str] = {}
        self.unavailable_reason: Optional[str] = None
        self._consecutive_failures = 0
        self._tripped = False

    # ------------------------------------------------------------------ #
    # Availability
    # ------------------------------------------------------------------ #
    def available(self) -> bool:
        """Is the Claude Code CLI present and is the agent pass enabled?"""
        if not self.cfg.agent_enabled:
            self.unavailable_reason = "agent disabled by config"
            return False
        if self._runner is not None:
            return True
        try:
            from ..claude_cli import cli_available
        except Exception as exc:  # pragma: no cover - defensive
            self.unavailable_reason = f"claude_cli import failed: {exc}"
            return False
        if not cli_available():
            self.unavailable_reason = (
                "Claude Code CLI not found on PATH — install Claude Code or set "
                "AIEO_CLAUDE_CLI_BIN (analysis falls back to heuristics)"
            )
            return False
        return True

    # ------------------------------------------------------------------ #
    # Per-page loop
    # ------------------------------------------------------------------ #
    def analyze_nodes(self, nodes: Sequence[ContextNode]) -> Dict[str, Any]:
        """Analyze every extracted node; returns a stats dict for the manifest."""
        targets = [n for n in nodes if n.extracted and not n.error]
        stats: Dict[str, Any] = {
            "candidates": len(targets),
            "agent_calls": 0,
            "agent_ok": 0,
            "agent_failed": 0,
            "heuristic": 0,
            "model": None,
            "provider": "claude-cli (OAuth)",
        }
        if not targets:
            stats["skipped_reason"] = "no extracted pages"
            return stats

        if not self.available():
            for node in targets:
                self._apply_heuristic(node)
            stats["heuristic"] = len(targets)
            stats["skipped_reason"] = self.unavailable_reason
            return stats

        selected = self._select(targets)
        stats["agent_calls"] = len(selected)
        stats["model"] = self.cfg.agent_model or "default (sonnet)"
        selected_urls = {n.url for n in selected}

        workers = max(1, min(self.cfg.agent_concurrency, len(selected)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(self._analyze_one, selected))

        stats["agent_ok"] = sum(1 for ok in results if ok)
        stats["agent_failed"] = len(results) - stats["agent_ok"]

        for node in targets:
            if node.url not in selected_urls or node.analysis_method != "agent":
                self._apply_heuristic(node)
                stats["heuristic"] += 1

        if self._tripped:
            stats["circuit_breaker"] = (
                f"stopped calling the CLI after {_MAX_CONSECUTIVE_FAILURES} "
                "consecutive failures"
            )
        return stats

    def _analyze_one(self, node: ContextNode) -> bool:
        if self._tripped:
            return False
        payload = build_page_payload(node, self.cfg)
        try:
            raw = self._run(
                self._prompt(ANALYST_AGENT, _FALLBACK_ANALYST_PROMPT),
                json.dumps(payload, ensure_ascii=False, default=str),
            )
            result = parse_json(raw)
        except Exception as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                self._tripped = True
            node.analysis_error = f"{type(exc).__name__}: {exc}"[:300]
            logger.warning("Context agent failed for %s: %s", node.url, exc)
            return False
        self._consecutive_failures = 0
        node.analysis = result
        node.analysis_method = "agent"
        node.analysis_error = None
        return True

    # ------------------------------------------------------------------ #
    # Site-level synthesis
    # ------------------------------------------------------------------ #
    def synthesize(self, site) -> Dict[str, Any]:
        """One final call that turns the per-page analyses into a site picture."""
        if not self.cfg.agent_synthesis:
            return {}
        if self._tripped or not self.available():
            return heuristic_site_analysis(site)
        payload = build_site_payload(site, self.cfg)
        try:
            raw = self._run(
                self._prompt(SYNTHESIZER_AGENT, _FALLBACK_SYNTHESIS_PROMPT),
                json.dumps(payload, ensure_ascii=False, default=str),
            )
            result = parse_json(raw)
            result["_method"] = "agent"
            return result
        except Exception as exc:
            logger.warning("Context synthesis failed: %s", exc)
            fallback = heuristic_site_analysis(site)
            fallback["_error"] = f"{type(exc).__name__}: {exc}"[:300]
            return fallback

    # ------------------------------------------------------------------ #
    # Plumbing
    # ------------------------------------------------------------------ #
    def _run(self, system_prompt: str, user_prompt: str) -> str:
        if self._runner is not None:
            return self._runner(
                user_prompt,
                system_prompt=system_prompt,
                model=self.cfg.agent_model,
                timeout=self.cfg.agent_timeout,
            )
        from ..claude_cli import run_claude_cli

        return run_claude_cli(
            user_prompt,
            system_prompt=system_prompt,
            model=self.cfg.agent_model,
            timeout=self.cfg.agent_timeout,
        )

    def _prompt(self, agent_name: str, fallback: str) -> str:
        if agent_name in self._prompts:
            return self._prompts[agent_name]
        body = fallback
        try:
            if self._prompt_loader is None:
                from ..prompt_loader import PromptLoader

                self._prompt_loader = PromptLoader()
            item = self._prompt_loader.get_collection_item("agents", agent_name)
            if item and item.get("body"):
                body = item["body"]
        except Exception as exc:  # pragma: no cover - prompts ship with the repo
            logger.warning(
                "Falling back to built-in prompt for %s: %s", agent_name, exc
            )
        self._prompts[agent_name] = body
        return body

    def _select(self, nodes: Sequence[ContextNode]) -> List[ContextNode]:
        """Pick which pages get a real agent call: seed first, then importance."""
        limit = max(1, self.cfg.agent_max_pages)
        if len(nodes) <= limit:
            return list(nodes)

        def rank(node: ContextNode):
            words = (node.content or {}).get("word_count", 0)
            return (
                0 if node.depth == 0 else 1,
                -len(node.parents),
                node.depth,
                -words,
                node.url,
            )

        return sorted(nodes, key=rank)[:limit]

    def _apply_heuristic(self, node: ContextNode) -> None:
        if node.analysis_method == "agent":
            return
        node.analysis = heuristic_page_analysis(node)
        node.analysis_method = "heuristic"


# --------------------------------------------------------------------------- #
# Payload builders (what the agent actually sees)
# --------------------------------------------------------------------------- #
def build_page_payload(node: ContextNode, cfg: ContextConfig) -> Dict[str, Any]:
    """A compact, bounded bundle: structure + metadata + presentation + text."""
    content = node.content or {}
    presentation = node.presentation or {}
    styles = presentation.get("styles", {})
    images = presentation.get("images", {})
    animation = presentation.get("animation", {})
    interactivity = presentation.get("interactivity", {})
    seo = node.seo or {}
    links = node.links or {}

    excerpt = (content.get("text") or "")[: max(500, cfg.agent_max_chars)]
    return {
        "task": "analyze_page_context",
        "page": {
            "url": node.url,
            "path": node.path,
            "depth_from_seed": node.depth,
            "discovered_via": node.discovery_source,
            "title": node.title,
            "description": node.description,
            "is_index_page": node.is_index,
            "word_count": content.get("word_count"),
            "reading_time_min": content.get("reading_time_min"),
        },
        "position_in_site": {
            "linked_from": node.parents[:5],
            "anchor_texts_pointing_here": node.anchor_texts[:5],
            "links_out_to": node.children[:15],
        },
        "metadata": {
            "lang": (node.meta or {}).get("lang"),
            "canonical": seo.get("canonical", {}).get("href"),
            "author": seo.get("author"),
            "dates": seo.get("dates"),
            "keywords": seo.get("keywords", [])[:20],
            "categories": seo.get("categories", [])[:20],
            "open_graph": (seo.get("open_graph", {}) or {}).get("values", {}),
            "structured_data_types": (seo.get("structured_data", {}) or {}).get(
                "types", []
            ),
        },
        "seo_facts": {
            "title_length": (seo.get("title", {}) or {}).get("length"),
            "description_length": (seo.get("description", {}) or {}).get("length"),
            "indexable": seo.get("indexable"),
            "headings": (seo.get("headings", {}) or {}).get("counts"),
            "heading_outline": (seo.get("headings", {}) or {}).get("outline", [])[:20],
            "internal_links": (seo.get("links", {}) or {}).get("internal"),
            "external_links": (seo.get("links", {}) or {}).get("external"),
            "detected_issues": seo.get("issues", [])[:15],
        },
        "presentation": {
            "css_frameworks": styles.get("frameworks"),
            "palette": [c["color"] for c in (styles.get("palette") or [])][:8],
            "fonts": styles.get("font_families"),
            "breakpoints": styles.get("breakpoints"),
            "dark_mode": styles.get("dark_mode"),
            "layout": {
                "flexbox": styles.get("uses_flexbox"),
                "grid": styles.get("uses_grid"),
                "media_queries": styles.get("media_queries"),
            },
            "images": {
                "count": images.get("count"),
                "formats": images.get("formats"),
                "alt_coverage": images.get("alt_coverage"),
                "lazy_loaded": images.get("lazy_loaded"),
                "responsive_srcset": images.get("responsive_srcset"),
                "inline_svg": images.get("inline_svg"),
                "samples": [
                    {"src": i.get("src"), "alt": i.get("alt")}
                    for i in (images.get("items") or [])[:8]
                ],
            },
            "animation": {
                "has_motion": animation.get("has_motion"),
                "signals": animation.get("signals"),
                "keyframes": (animation.get("keyframes") or [])[:10],
                "libraries": animation.get("libraries"),
                "respects_reduced_motion": animation.get("respects_reduced_motion"),
                "script_driven": {
                    k: animation.get(k)
                    for k in (
                        "request_animation_frame",
                        "canvas_drawing",
                        "svg_scripted",
                        "web_animations_api",
                    )
                },
            },
            "interactivity": {
                "has_interactive_ui": interactivity.get("has_interactive_ui"),
                "signals": interactivity.get("signals"),
                "demo_sections": interactivity.get("demo_sections"),
                "controls": interactivity.get("controls"),
                "control_types": interactivity.get("control_types"),
                "control_labels": (interactivity.get("labels") or [])[:15],
                "file_uploads": interactivity.get("file_uploads"),
                "progressive_enhancement": interactivity.get("progressive_enhancement"),
                "event_listeners": interactivity.get("event_listeners"),
            },
            "js_frameworks": (presentation.get("scripts", {}) or {}).get("frameworks"),
        },
        "downloads": [
            {"url": a.get("url"), "type": a.get("type"), "format": a.get("format")}
            for a in (node.assets or [])
            if a.get("type") in ("source", "archive", "document", "data")
        ][:20],
        "references": {
            "internal_sample": [
                {"url": lnk.get("url"), "text": lnk.get("text")}
                for lnk in (links.get("internal") or [])[:20]
            ],
            "external_sample": [
                {"url": lnk.get("url"), "domain": lnk.get("domain")}
                for lnk in (links.get("external") or [])[:15]
            ],
        },
        "content_excerpt": excerpt,
        "content_truncated": len(content.get("text") or "") > len(excerpt),
    }


def build_site_payload(site, cfg: ContextConfig) -> Dict[str, Any]:
    """Compact whole-site bundle for the synthesis call."""
    nodes = [n for n in site.nodes if n.extracted]
    pages = []
    for node in nodes[:120]:
        analysis = node.analysis or {}
        pages.append(
            {
                "url": node.url,
                "depth": node.depth,
                "title": node.title,
                "is_index": node.is_index,
                "word_count": (node.content or {}).get("word_count"),
                "interactive": bool(
                    ((node.presentation or {}).get("interactivity") or {}).get(
                        "has_interactive_ui"
                    )
                ),
                "page_type": analysis.get("page_type"),
                "topics": (analysis.get("topics") or [])[:6],
                "summary": (analysis.get("summary") or node.description or "")[:280],
                "analysis_method": node.analysis_method,
            }
        )
    return {
        "task": "synthesize_site_context",
        "seed_url": site.seed_url,
        "root_host": site.root_host,
        "crawl": {
            "depth_requested": (site.config or {}).get("depth"),
            "scope": (site.config or {}).get("scope"),
            "stats": site.stats,
            "depth_histogram": site.depth_histogram,
        },
        "pages": pages,
        "structure": {
            "hubs": site.hubs[:10],
            "orphans": site.orphans[:20],
            "edge_count": len(site.edges),
        },
        "external_references": site.external_references[:25],
        "style_profile": site.style_profile,
        "animation_profile": site.animation_profile,
        "interactivity_profile": site.interactivity_profile,
        "seo_profile": {
            k: v
            for k, v in (site.seo_profile or {}).items()
            if k
            in (
                "pages_analyzed",
                "issue_counts",
                "severity_counts",
                "schema_types",
                "avg_word_count",
                "indexable_pages",
                "duplicate_titles",
            )
        },
    }


# --------------------------------------------------------------------------- #
# Heuristic fallbacks (no CLI, no key, still a usable dataset)
# --------------------------------------------------------------------------- #
_TYPE_HINTS = (
    ("article", r"\b(article|blogposting|newsarticle|techarticle)\b"),
    ("documentation", r"/docs?/|/documentation/|/reference/|/api/"),
    ("product", r"\bproduct\b|/pricing|/plans"),
    ("about", r"/about|/team|/company"),
    ("contact", r"/contact"),
)


def heuristic_page_analysis(node: ContextNode) -> Dict[str, Any]:
    """Deterministic stand-in for the agent's per-page JSON."""
    seo = node.seo or {}
    presentation = node.presentation or {}
    animation = presentation.get("animation", {})
    content = node.content or {}
    jsonld = " ".join((seo.get("structured_data", {}) or {}).get("types", []))
    hay = f"{jsonld} {node.path}".lower()

    page_type = "index" if node.is_index else "page"
    for label, pattern in _TYPE_HINTS:
        if re.search(pattern, hay):
            page_type = label
            break

    topics = list(
        dict.fromkeys(
            (seo.get("keywords") or [])
            + (seo.get("categories") or [])
            + [
                h["text"]
                for h in (seo.get("headings", {}) or {}).get("outline", [])[:5]
                if h.get("text")
            ]
        )
    )[:8]

    high = [i for i in seo.get("issues", []) if i["severity"] == "high"]
    medium = [i for i in seo.get("issues", []) if i["severity"] == "medium"]

    return {
        "page_type": page_type,
        "topics": topics,
        "entities": [],
        "audience": None,
        "summary": (content.get("summary") or node.description or node.title or "")[
            :400
        ],
        "key_points": [
            h["text"]
            for h in (seo.get("headings", {}) or {}).get("outline", [])[1:6]
            if h.get("text")
        ],
        "seo_assessment": {
            "strengths": _heuristic_strengths(seo),
            "issues": [i["message"] for i in high + medium][:6],
            "priority_fixes": [i["code"] for i in high][:3],
        },
        "design_notes": {
            "style": ", ".join(
                (presentation.get("styles", {}) or {}).get("frameworks") or []
            )
            or "no framework detected",
            "imagery": f"{(presentation.get('images', {}) or {}).get('count', 0)} images",
            "motion": "; ".join(animation.get("signals") or []) or "unknown",
        },
        "relationships": [
            {"target": url, "relation": "links_to"} for url in node.children[:10]
        ],
        "confidence": 0.35,
        "_method": "heuristic",
    }


def _heuristic_strengths(seo: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    if (seo.get("title", {}) or {}).get("status") == "ok":
        out.append("well-sized title")
    if (seo.get("description", {}) or {}).get("status") == "ok":
        out.append("well-sized meta description")
    if (seo.get("structured_data", {}) or {}).get("types"):
        out.append("structured data present")
    if (seo.get("headings", {}) or {}).get("outline_ok"):
        out.append("clean heading outline")
    if (seo.get("open_graph", {}) or {}).get("complete"):
        out.append("complete Open Graph tags")
    return out


def heuristic_site_analysis(site) -> Dict[str, Any]:
    """Deterministic stand-in for the agent's site synthesis."""
    nodes = [n for n in site.nodes if n.extracted]
    topics: Dict[str, int] = {}
    types: Dict[str, int] = {}
    for node in nodes:
        for topic in (node.analysis or {}).get("topics", [])[:6]:
            topics[topic] = topics.get(topic, 0) + 1
        page_type = (node.analysis or {}).get("page_type") or "page"
        types[page_type] = types.get(page_type, 0) + 1

    top_topics = [t for t, _ in sorted(topics.items(), key=lambda kv: -kv[1])[:12]]
    return {
        "site_purpose": site.seed_url,
        "audience": None,
        "content_taxonomy": [
            {
                "cluster": topic,
                "pages": [
                    n.url
                    for n in nodes
                    if topic in (n.analysis or {}).get("topics", [])
                ][:10],
            }
            for topic in top_topics[:6]
        ],
        "page_type_distribution": types,
        "information_architecture": {
            "pattern": "hub-and-spoke" if site.hubs else "flat",
            "depth_reached": site.stats.get("max_depth_reached"),
            "hubs": [h.get("url") for h in site.hubs[:5]],
            "orphans": site.orphans[:10],
        },
        "design_system": {
            "palette": (site.style_profile or {}).get("palette", [])[:6],
            "fonts": (site.style_profile or {}).get("font_families", [])[:5],
            "frameworks": (site.style_profile or {}).get("frameworks", []),
            "motion_language": (site.animation_profile or {}).get("summary"),
        },
        "seo_posture": {
            "top_issues": list(
                (site.seo_profile or {}).get("issue_counts", {}).items()
            )[:6],
            "indexable_pages": (site.seo_profile or {}).get("indexable_pages"),
        },
        "context_brief": (
            f"{len(nodes)} pages mapped {site.stats.get('max_depth_reached', 0)} level(s) "
            f"below {site.seed_url}. Dominant topics: {', '.join(top_topics[:5]) or 'n/a'}."
        ),
        "_method": "heuristic",
    }


# --------------------------------------------------------------------------- #
# Tolerant JSON parsing of model output
# --------------------------------------------------------------------------- #
def parse_json(raw: str) -> Dict[str, Any]:
    """Parse the agent's JSON reply, tolerating code fences and stray prose."""
    cleaned = (raw or "").strip()
    if not cleaned:
        raise ValueError("agent returned empty output")
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise ValueError(f"agent returned non-JSON output: {cleaned[:200]}")
        parsed = json.loads(match.group())
    if not isinstance(parsed, dict):
        raise ValueError("agent returned JSON that is not an object")
    return parsed
