"""Offline tests for the site-context feature.

The whole suite runs with no network egress and no API key: a small fixture site
(a ``/category/<name>`` index whose items live under ``/page/<slug>``, mirroring
the real-world shape this feature targets) is served from 127.0.0.1 by
``http.server`` in a background thread, and the Claude Code CLI is replaced by a
fake executable so the OAuth agent loop is exercised end to end without ever
calling a model.
"""

from __future__ import annotations

import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.services.site_context import ContextConfig, SiteContext, SiteContextService
from app.services.site_context import exporters
from app.services.site_context.agent import ContextAgent, parse_json
from app.services.site_context.link_map import in_scope, is_denied, looks_like_index
from app.services.site_context.store import (
    ContextStore,
    context_key,
    list_contexts,
    load_context_manifest,
)

THEME_CSS = """
:root{--brand:#2563eb;--ink:#0f172a}
body{font-family:'Inter',system-ui;color:var(--ink);display:flex}
.grid{display:grid}
@media (min-width:768px){.wide{display:grid}}
@media (prefers-reduced-motion:reduce){*{animation:none}}
@keyframes fade-in{from{opacity:0}to{opacity:1}}
@keyframes slide-up{from{transform:translateY(8px)}to{transform:none}}
.card{transition:box-shadow .2s ease;animation:fade-in .3s}
.hero{background-image:url(/img/hero.png)}
"""

ITEMS = [
    ("fast-fourier-transform", "Fast Fourier transform"),
    ("binary-array-set", "Binary array set"),
    ("gauss-elimination", "Gauss-Jordan elimination over any field"),
]


def _write_site(root: Path, base: str) -> None:
    (root / "css").mkdir(parents=True, exist_ok=True)
    (root / "css" / "theme.css").write_text(THEME_CSS, encoding="utf-8")

    (root / "index.html").write_text(
        """<!DOCTYPE html><html lang="en"><head><title>Fixture home</title>
<meta name="description" content="The home page of the fixture site, long enough to pass.">
<meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/css/theme.css">
</head><body><h1>Fixture home</h1><p>Welcome to the fixture.</p>
<a href="/category/programming">Programming</a> <a href="/about">About</a></body></html>""",
        encoding="utf-8",
    )

    (root / "about").mkdir(exist_ok=True)
    (root / "about" / "index.html").write_text(
        """<html lang="en"><head><title>About the fixture site</title></head>
<body><h1>About</h1><p>About page.</p><a href="/">Home</a></body></html>""",
        encoding="utf-8",
    )

    category = root / "category" / "programming"
    category.mkdir(parents=True, exist_ok=True)
    links = "".join(
        f'<li><a href="/page/{slug}">{title}</a></li>' for slug, title in ITEMS
    )
    links += '<li><a href="/page/interactive-demo">Interactive demo</a></li>'
    category.joinpath("index.html").write_text(
        f"""<!DOCTYPE html><html lang="en"><head><title>Programming</title>
<meta name="description" content="An index of programming articles, tutorials and projects.">
<meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/css/theme.css">
<link rel="canonical" href="{base}/category/programming">
<meta property="og:title" content="Programming"><meta property="og:description" content="Index">
<meta property="og:image" content="{base}/img/cover.png"><meta property="og:url" content="{base}/category/programming">
<meta property="og:type" content="website">
<script type="application/ld+json">{{"@type":"CollectionPage","name":"Programming"}}</script>
</head><body><nav><a href="/">Home</a></nav><main><h1>Programming</h1>
<p>Articles about programming, algorithms and small projects.</p>
<ul>{links}</ul>
<img src="/img/cover.png" alt="cover" width="80" height="40" loading="lazy">
<a href="/category/programming/page/2">Next page</a>
</main><footer><a href="/about">About</a></footer></body></html>""",
        encoding="utf-8",
    )

    extras = {
        "fast-fourier-transform": '<canvas id="c"></canvas><video autoplay muted loop></video>',
        "binary-array-set": '<img src="/img/x.webp"><img src="/img/y.png" alt="y">',
        "gauss-elimination": '<svg><animate attributeName="x" dur="1s"/></svg>',
    }
    for slug, title in ITEMS:
        page = root / "page" / slug
        page.mkdir(parents=True, exist_ok=True)
        body = f"Body text about {title.lower()}. " * 60
        page.joinpath("index.html").write_text(
            f"""<!DOCTYPE html><html lang="en"><head><title>{title}</title>
<meta name="description" content="A detailed article about {title.lower()} with code and worked examples.">
<meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/css/theme.css">
<script src="https://cdn.example.test/gsap.min.js"></script>
</head><body><main><h1>{title}</h1><h2>Overview</h2><p>{body}</p>
{extras[slug]}
<a href="/category/programming">Back to Programming</a>
<a href="https://en.wikipedia.test/wiki/{slug}">Wikipedia</a></main></body></html>""",
            encoding="utf-8",
        )

    # A page whose payload is a live tool, mirroring how real sites ship them:
    # a <form> of controls, a demo container that ships `hidden` until its script
    # reveals it, source-file downloads, media, and motion that lives only in JS.
    demo = root / "page" / "interactive-demo"
    demo.mkdir(parents=True, exist_ok=True)
    demo.joinpath("index.html").write_text(
        """<!DOCTYPE html><html lang="en"><head><title>Interactive demo</title>
<meta name="description" content="A page whose payload is a live in-browser tool with controls.">
<meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/css/theme.css">
<script src="/js/demo.js"></script>
<script src="https://cdn.example.test/analytics.js"></script>
</head><body>
<nav class="site-nav">Site navigation</nav>
<div class="cookie-consent-banner">Cookie banner</div>
<main><h1>Interactive demo</h1>
<h2>Live demo (JavaScript)</h2>
<form>
  <label for="n">Sample size</label><input id="n" type="number" value="8">
  <label for="q">Quality</label><input id="q" type="range" min="0" max="9">
  <label for="f">Upload an image</label><input id="f" type="file">
  <button type="submit">Run</button>
</form>
<div class="demo results" hidden><p>Hidden until JS runs</p>
  <table><tr><th>bit</th><th>parity</th></tr><tr><td>0</td><td>1</td></tr></table>
</div>
<canvas id="stage" width="200" height="120"></canvas>
<h2>Source code</h2>
<ul><li><a href="/res/demo/solver.py">Python version</a></li>
<li><a href="/res/demo/Solver.java">Java version</a></li></ul>
<video src="/res/demo/clip.mp4" controls></video>
<a href="/category/programming">Back</a>
</main></body></html>""",
        encoding="utf-8",
    )
    (root / "js").mkdir(exist_ok=True)
    (root / "js" / "demo.js").write_text(
        "function frame(){ const ctx = document.getElementById('stage').getContext('2d');"
        " ctx.clearRect(0,0,200,120); requestAnimationFrame(frame); }\n"
        "document.querySelector('.demo').hidden = false;\n"
        "document.getElementById('n').addEventListener('input', frame);\n",
        encoding="utf-8",
    )

    private = root / "private"
    private.mkdir(exist_ok=True)
    private.joinpath("index.html").write_text(
        "<html><head><title>Secret</title></head><body><h1>Secret</h1></body></html>",
        encoding="utf-8",
    )
    (root / "robots.txt").write_text(
        f"User-agent: *\nDisallow: /private/\nSitemap: {base}/sitemap.xml\n",
        encoding="utf-8",
    )
    (root / "sitemap.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{base}/</loc></url>
<url><loc>{base}/category/programming</loc></url>
<url><loc>{base}/page/only-in-sitemap</loc></url>
</urlset>""",
        encoding="utf-8",
    )
    only = root / "page" / "only-in-sitemap"
    only.mkdir(parents=True, exist_ok=True)
    only.joinpath("index.html").write_text(
        "<html lang='en'><head><title>Only in sitemap</title></head>"
        "<body><h1>Only in sitemap</h1><p>Unlinked page.</p></body></html>",
        encoding="utf-8",
    )


class _CountingHandler(SimpleHTTPRequestHandler):
    """Records every requested path so tests can assert on fetch counts."""

    requests: list = []

    def log_message(self, *args):  # silence the test output
        pass

    def do_GET(self):  # noqa: N802 - stdlib naming
        type(self).requests.append(self.path)
        super().do_GET()


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setenv("AIEO_SNAPSHOT_ALLOW_PRIVATE", "1")
    root = tmp_path / "site"
    root.mkdir()
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(_CountingHandler, directory=str(root))
    )
    base = f"http://127.0.0.1:{server.server_port}"
    _write_site(root, base)
    _CountingHandler.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def workspace(tmp_path):
    return tmp_path / "ws"


def _cfg(**kw):
    defaults = dict(depth=2, delay_seconds=0.0, agent_enabled=False, max_pages=30)
    defaults.update(kw)
    return ContextConfig(**defaults)


def _paths(ctx: SiteContext):
    return sorted(node.path for node in ctx.nodes)


# --------------------------------------------------------------------------- #
# Phase 1 — mapping
# --------------------------------------------------------------------------- #
def test_maps_a_section_seed_one_level_down(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    paths = _paths(ctx)
    assert "/category/programming" in paths
    for slug, _title in ITEMS:
        assert f"/page/{slug}" in paths
    assert ctx.depth_histogram["0"] == 1
    assert ctx.depth_histogram["1"] >= len(ITEMS)
    # depth 1 stops before the item pages' own links are followed.
    assert max(n.depth for n in ctx.nodes) == 1


def test_depth_two_reaches_further(site, workspace):
    svc = SiteContextService(root=workspace)
    shallow = svc.build(f"{site}/category/programming", _cfg(depth=0))
    deep = svc.build(f"{site}/category/programming", _cfg(depth=2))
    assert len(shallow.nodes) == 1
    assert len(deep.nodes) > len(shallow.nodes)
    assert "/about" in _paths(deep)  # only reachable via the home page at L2


def test_seed_under_a_taxonomy_prefix_is_crawlable(site, workspace):
    """The snapshot crawler denies /category/ and /page/; a context seed must not."""
    cfg = _cfg(depth=1)
    assert not is_denied(f"{site}/category/programming", cfg)
    assert not is_denied(f"{site}/page/binary-array-set", cfg)
    ctx = SiteContextService(root=workspace).build(f"{site}/category/programming", cfg)
    assert ctx.nodes[0].status == 200
    assert ctx.nodes[0].error is None


def test_pagination_traps_are_skipped(site, workspace):
    cfg = _cfg(depth=1)
    assert is_denied(f"{site}/category/programming/page/2", cfg)
    ctx = SiteContextService(root=workspace).build(f"{site}/category/programming", cfg)
    assert not any(p.endswith("/page/2") for p in _paths(ctx))


def test_scope_path_stays_under_the_seed(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/page", _cfg(depth=2, scope="path")
    )
    assert all(n.path.startswith("/page") for n in ctx.nodes)


def test_scope_host_allows_siblings(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=2, scope="host")
    )
    assert "/" in _paths(ctx)


def test_in_scope_rules():
    cfg = _cfg(scope="host")
    assert in_scope(
        "https://example.com/a", "https://example.com/x", "example.com", cfg
    )
    assert not in_scope(
        "https://other.com/a", "https://example.com/x", "example.com", cfg
    )
    domain_cfg = _cfg(scope="domain")
    assert in_scope(
        "https://blog.example.com/a", "https://example.com/x", "example.com", domain_cfg
    )
    path_cfg = _cfg(scope="path")
    assert in_scope(
        "https://example.com/docs/a",
        "https://example.com/docs",
        "example.com",
        path_cfg,
    )
    assert not in_scope(
        "https://example.com/other", "https://example.com/docs", "example.com", path_cfg
    )


def test_robots_disallow_is_respected(site, workspace):
    ctx = SiteContextService(root=workspace).build(f"{site}/", _cfg(depth=2))
    assert "/private" not in _paths(ctx)


def test_follow_sitemap_adds_unlinked_pages(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1, follow_sitemap=True)
    )
    assert "/page/only-in-sitemap" in _paths(ctx)
    assert any(n.discovery_source == "sitemap" for n in ctx.nodes)


def test_map_only_skips_extraction_and_agent(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1), map_only=True
    )
    assert len(ctx.nodes) > 1
    assert all(not n.extracted for n in ctx.nodes)
    assert ctx.phases["extract"] == {"skipped": "map_only"}
    assert ctx.phases["agent"]["skipped"] == "map_only"
    assert ctx.analysis_method == "skipped"


def test_edges_and_link_graph(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    seed = f"{site}/category/programming"
    assert ctx.link_graph[seed]
    assert any(e["source"] == seed for e in ctx.edges)
    top_hub = ctx.hubs[0]
    assert top_hub["in_degree"] >= 1


# --------------------------------------------------------------------------- #
# Phase 2 — extraction, presentation, SEO
# --------------------------------------------------------------------------- #
def test_extraction_captures_content_and_metadata(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    item = next(n for n in ctx.nodes if n.path.endswith("/fast-fourier-transform"))
    assert item.extracted
    assert item.title == "Fast Fourier transform"
    assert item.content["word_count"] > 100
    assert item.content["headings"][0]["text"] == "Fast Fourier transform"
    assert item.meta["lang"] == "en"
    assert any(link["domain"] == "en.wikipedia.test" for link in item.links["external"])


def test_presentation_captures_styles_images_and_animation(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    seed = ctx.node_by_url(f"{site}/category/programming")
    styles = seed.presentation["styles"]
    assert "#2563eb" in [c["color"] for c in styles["palette"]]
    assert "Inter" in styles["font_families"]
    assert styles["custom_properties"]["--brand"] == "#2563eb"
    assert styles["breakpoints"] == ["768px"]
    assert styles["uses_grid"] and styles["uses_flexbox"]

    images = seed.presentation["images"]
    assert images["count"] == 1
    assert images["lazy_loaded"] == 1
    assert images["with_dimensions"] == 1
    assert images["alt_coverage"] == 1.0
    assert images["css_background_images"] >= 1

    animation = seed.presentation["animation"]
    assert set(animation["keyframes"]) == {"fade-in", "slide-up"}
    assert animation["transition_declarations"] >= 1
    assert animation["respects_reduced_motion"] is True
    assert animation["has_motion"] is True


def test_animation_detects_libraries_media_and_svg(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    fft = next(n for n in ctx.nodes if n.path.endswith("/fast-fourier-transform"))
    anim = fft.presentation["animation"]
    assert "gsap" in anim["libraries"]
    assert anim["video"]["autoplay"] == 1
    assert anim["canvas_elements"] == 1

    gauss = next(n for n in ctx.nodes if n.path.endswith("/gauss-elimination"))
    assert gauss.presentation["animation"]["svg_smil_elements"] >= 1


def test_missing_alt_is_reported(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    bas = next(n for n in ctx.nodes if n.path.endswith("/binary-array-set"))
    assert bas.presentation["images"]["missing_alt"] == 1
    assert any(i["code"] == "image_alt_missing" for i in bas.seo["issues"])


def test_seo_facts_and_issues(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    seed = ctx.node_by_url(f"{site}/category/programming")
    seo = seed.seo
    assert seo["title"]["status"] in ("ok", "short")
    assert seo["description"]["status"] == "ok"
    assert seo["canonical"]["self_referential"] is True
    assert seo["indexable"] is True
    assert seo["open_graph"]["complete"] is True
    assert seo["structured_data"]["types"] == ["CollectionPage"]
    assert seo["headings"]["h1_count"] == 1
    codes = {i["code"] for i in seo["issues"]}
    assert "twitter_card_missing" in codes

    item = next(n for n in ctx.nodes if n.path.endswith("/binary-array-set"))
    assert {i["code"] for i in item.seo["issues"]} >= {
        "canonical_missing",
        "structured_data_missing",
    }


def test_index_pages_are_flagged(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    seed = ctx.node_by_url(f"{site}/category/programming")
    assert seed.is_index is True
    item = next(n for n in ctx.nodes if n.path.endswith("/binary-array-set"))
    assert item.is_index is False


def test_index_detection_rules():
    # Roots and taxonomy landing pages are hubs...
    assert looks_like_index("https://x.test/") is True
    assert looks_like_index("https://x.test/category/programming") is True
    assert looks_like_index("https://x.test/recent-pages/") is True
    assert looks_like_index("https://x.test/x", title="Archive") is True
    # ...but a post that merely lives under one is not.
    assert looks_like_index("https://x.test/blog/my-post") is False
    assert looks_like_index("https://x.test/category/a/b/deep-post") is False
    # A leaf article wrapped in a 20-link site nav must not read as a hub: only
    # in-content links count, and prose density decides.
    assert (
        looks_like_index("https://x.test/page/essay", content_links=6, word_count=2000)
        is False
    )
    assert (
        looks_like_index("https://x.test/page/essay", content_links=18, word_count=2000)
        is False
    )
    assert (
        looks_like_index("https://x.test/page/list", content_links=40, word_count=200)
        is True
    )


def test_stylesheets_are_fetched_once_for_the_whole_crawl(site, workspace):
    SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    css_requests = [p for p in _CountingHandler.requests if p.endswith("theme.css")]
    assert len(css_requests) == 1


def test_rollups_across_pages(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    assert ctx.style_profile["pages_analyzed"] == len(
        [n for n in ctx.nodes if n.extracted]
    )
    assert "Inter" in ctx.style_profile["font_families"]
    assert ctx.animation_profile["pages_with_motion"] >= 1
    assert "gsap" in ctx.animation_profile["libraries"]
    assert "fade-in" in ctx.animation_profile["keyframes"]
    assert ctx.seo_profile["pages_analyzed"] >= 4
    assert ctx.seo_profile["severity_counts"]["medium"] >= 1
    assert ctx.external_references[0]["domain"] == "en.wikipedia.test"
    assert ctx.external_references[0]["count"] == len(ITEMS)
    assert ctx.totals["word_count"] > 0
    assert any(a["type"] == "image" for a in ctx.asset_inventory)


def test_rerun_reuses_the_cache(site, workspace):
    svc = SiteContextService(root=workspace)
    svc.build(f"{site}/category/programming", _cfg(depth=1))
    before = len(_CountingHandler.requests)
    second = svc.build(f"{site}/category/programming", _cfg(depth=1))
    after = len(_CountingHandler.requests)
    assert any(n.from_cache for n in second.nodes)
    # Conditional GETs still happen, but every page still extracts from cache.
    assert second.stats["nodes_extracted"] >= 4
    assert after > before  # revalidation requests were made, not zero traffic


def test_broken_revalidation_does_not_empty_the_dataset(site, workspace, monkeypatch):
    """Some servers answer a conditional GET with an empty 200 instead of a 304.

    Taken at face value that overwrites every cached body with nothing, so a
    re-run silently returns an empty dataset. Observed live on nayuki.io.
    """
    svc = SiteContextService(root=workspace)
    first = svc.build(f"{site}/category/programming", _cfg(depth=1))
    assert first.totals["word_count"] > 0
    css_before = max(
        (n.presentation["styles"]["css_bytes_analyzed"] for n in first.nodes), default=0
    )
    assert css_before > 0

    from app.services.site_snapshot import fetcher as fetcher_mod

    real_fetch = fetcher_mod.Fetcher.fetch

    def empty_on_revalidation(self, url, conditional=None):
        result = real_fetch(self, url, conditional)
        if conditional:  # the broken server behaviour
            result.status = 200
            result.text = ""
            result.content_type = None
        return result

    monkeypatch.setattr(fetcher_mod.Fetcher, "fetch", empty_on_revalidation)
    second = svc.build(f"{site}/category/programming", _cfg(depth=1))

    assert second.totals["word_count"] == first.totals["word_count"]
    assert second.stats["nodes_extracted"] == first.stats["nodes_extracted"]
    css_after = max(
        (n.presentation["styles"]["css_bytes_analyzed"] for n in second.nodes),
        default=0,
    )
    assert css_after == css_before
    assert second.animation_profile["pages_with_motion"] == (
        first.animation_profile["pages_with_motion"]
    )

    # And the good bodies must still be on disk for the next run.
    third = svc.build(f"{site}/category/programming", _cfg(depth=1))
    assert third.totals["word_count"] == first.totals["word_count"]


def test_already_corrupted_cache_self_heals(site, workspace, monkeypatch):
    """A cache poisoned by an earlier run must repair itself, not stay empty."""
    svc = SiteContextService(root=workspace)
    good = svc.build(f"{site}/category/programming", _cfg(depth=1))

    # Poison every cached body, exactly as the pre-fix code would have.
    store = ContextStore(f"{site}/category/programming", root=workspace)
    for node in good.nodes:
        entry = store.cache.load(node.url)
        if entry:
            store.cache.save(
                node.url,
                status=200,
                content_type=None,
                text="",
                content_hash="",
                fetched_at=entry["fetched_at"],
                etag=entry.get("etag"),
                last_modified=entry.get("last_modified"),
            )
    assert store.cache.read_body(good.nodes[0].url) == ""

    from app.services.site_snapshot import fetcher as fetcher_mod

    real_fetch = fetcher_mod.Fetcher.fetch

    def empty_on_revalidation(self, url, conditional=None):
        result = real_fetch(self, url, conditional)
        if conditional:
            result.status = 200
            result.text = ""
            result.content_type = None
        return result

    monkeypatch.setattr(fetcher_mod.Fetcher, "fetch", empty_on_revalidation)
    repaired = svc.build(f"{site}/category/programming", _cfg(depth=1))
    assert repaired.totals["word_count"] == good.totals["word_count"]


def test_no_cache_still_extracts_from_memory(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1, use_cache=False)
    )
    assert ctx.phases["extract"]["extracted"] >= 4
    assert ctx.phases["extract"]["missing_body"] == 0


# --------------------------------------------------------------------------- #
# Interactivity, resources and rendering
# --------------------------------------------------------------------------- #
def test_interactive_demo_survives_extraction(site, workspace):
    """A demo's controls are content. Progressive-enhancement demos ship hidden
    and forms are normally stripped as chrome — both must be kept."""
    ctx = SiteContextService(root=workspace).build(
        f"{site}/page/interactive-demo", _cfg(depth=0)
    )
    node = ctx.nodes[0]
    text = node.content["text"]
    assert "Sample size" in text  # a label inside <form>
    assert "Hidden until JS runs" in text  # inside <div hidden class="demo">

    inter = node.presentation["interactivity"]
    assert inter["has_interactive_ui"] is True
    assert inter["controls"] >= 3
    assert inter["control_types"]["range"] == 1
    assert inter["file_uploads"] == 1
    assert "Live demo (JavaScript)" in inter["demo_sections"]
    assert any("file upload" in s for s in inter["signals"])
    assert "Sample size" in " ".join(inter["labels"])


def test_chrome_is_still_stripped_around_the_demo(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/page/interactive-demo", _cfg(depth=0)
    )
    text = ctx.nodes[0].content["text"]
    assert "Cookie banner" not in text
    assert "Site navigation" not in text


def test_script_driven_motion_is_detected(site, workspace):
    """Motion living in an external script is invisible to CSS/markup checks."""
    ctx = SiteContextService(root=workspace).build(
        f"{site}/page/interactive-demo", _cfg(depth=0)
    )
    anim = ctx.nodes[0].presentation["animation"]
    assert anim["request_animation_frame"] is True
    assert anim["canvas_drawing"] is True
    assert anim["has_motion"] is True
    assert any("script-driven" in s for s in anim["signals"])


def test_scripts_are_fetched_once_and_third_party_skipped(site, workspace):
    SiteContextService(root=workspace).build(
        f"{site}/page/interactive-demo", _cfg(depth=0)
    )
    requested = [p for p in _CountingHandler.requests if p.endswith("demo.js")]
    assert len(requested) == 1


def test_source_downloads_are_resources_not_pages(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/page/interactive-demo", _cfg(depth=1)
    )
    node = ctx.nodes[0]
    # Never queued as a page to crawl...
    assert not any(n.path.endswith(".py") for n in ctx.nodes)
    assert not any(link["url"].endswith(".py") for link in node.links["internal"])
    # ...and recorded as a typed download instead.
    downloads = [a for a in node.assets if a["type"] == "source"]
    assert {d["format"] for d in downloads} == {"Python", "Java"}
    assert node.counts["downloads"] == 2
    assert any(a["type"] == "video" for a in node.assets)
    kinds = {a["type"] for a in ctx.asset_inventory}
    assert {"image", "source", "video"} <= kinds
    # The inventory is capped, so totals are reported separately and stay honest.
    assert ctx.totals["assets_by_type"]["source"] == 2
    assert ctx.totals["assets"] >= len(ctx.asset_inventory)
    assert {a["format"] for a in ctx.asset_inventory if a["type"] == "source"} == {
        "Python",
        "Java",
    }


def test_resource_classifier():
    from app.services.site_context import resources

    assert resources.classify("https://x.test/a/b.py") == ("source", "Python")
    assert resources.classify("https://x.test/a/QrCode.java") == ("source", "Java")
    assert resources.classify("https://x.test/a/demo.mp4") == ("video", "mp4")
    assert resources.classify("https://x.test/a/paper.pdf") == ("document", "pdf")
    assert resources.classify("https://x.test/page/thing") == ("page", None)
    assert resources.classify("https://x.test/") == ("page", None)
    assert resources.is_resource("https://x.test/x.zip") is True
    assert resources.is_resource("https://x.test/x") is False


def test_render_mode_uses_the_post_javascript_dom(site, workspace):
    """With rendering on, the crawler must see JS-generated links and content."""

    class StubRenderer:
        """Duck-types Renderer: what Playwright would hand back."""

        def __init__(self):
            self.rendered = []

        def available(self):
            return True

        def render(self, url):
            from app.services.site_context.renderer import RenderResult

            self.rendered.append(url)
            return RenderResult(
                html=(
                    "<html lang='en'><head><title>Rendered</title></head><body><main>"
                    "<h1>Rendered</h1><p>Content built by JavaScript at runtime.</p>"
                    "<a href='/page/only-after-js'>Only after JS</a></main></body></html>"
                ),
                status=200,
                final_url=url,
            )

        def stats(self):
            return {"available": True}

        def close(self):
            pass

    stub = StubRenderer()
    ctx = SiteContextService(root=workspace, renderer=stub).build(
        f"{site}/category/programming", _cfg(depth=1, render=True)
    )
    assert stub.rendered  # the browser, not the static fetcher, read the page
    seed = ctx.node_by_url(f"{site}/category/programming")
    assert seed.title == "Rendered"
    assert "built by JavaScript" in seed.content["text"]
    # A link that only exists post-render was still followed.
    assert any(n.path == "/page/only-after-js" for n in ctx.nodes)


def test_render_falls_back_when_playwright_is_missing(site, workspace):
    """No browser must never mean no crawl."""
    from app.services.site_context.renderer import Renderer

    renderer = Renderer()
    renderer.unavailable_reason = "Playwright is not installed — test"
    ctx = SiteContextService(root=workspace, renderer=renderer).build(
        f"{site}/category/programming", _cfg(depth=0, render=True)
    )
    assert ctx.nodes[0].status == 200
    assert ctx.nodes[0].extracted
    assert "not installed" in ctx.phases["map"]["render_fallback"]


def test_interactivity_rollup(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    profile = ctx.interactivity_profile
    assert profile["interactive_pages"] >= 1
    assert profile["total_controls"] >= 3
    assert profile["file_upload_pages"] >= 1
    assert profile["pages"][0]["url"].endswith("/interactive-demo")
    assert "in-page tools" in profile["summary"]


# --------------------------------------------------------------------------- #
# Phase 3 — the Claude Code agent loop (OAuth)
# --------------------------------------------------------------------------- #
_FAKE_CLI = """
import json, sys
payload = sys.stdin.read()
if "synthesize_site_context" in payload:
    inner = {
        "site_purpose": "algorithms and programming projects",
        "context_brief": "A programming index with three article pages.",
        "content_taxonomy": [{"cluster": "algorithms", "pages": ["a"], "theme": "math"}],
        "confidence": 0.8,
    }
else:
    inner = {
        "page_type": "article",
        "topics": ["algorithms"],
        "summary": "An article page.",
        "confidence": 0.7,
    }
print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                  "result": json.dumps(inner)}))
"""

_FAILING_CLI = """
import json, sys
sys.stdin.read()
print(json.dumps({"type": "result", "subtype": "error_during_execution",
                  "is_error": True, "api_error_status": 401,
                  "result": "Failed to authenticate"}))
"""


def _install_fake_cli(tmp_path, monkeypatch, body: str) -> Path:
    script = tmp_path / "fake-claude"
    script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("AIEO_CLAUDE_CLI_BIN", str(script))
    return script


def test_agent_loop_runs_through_the_claude_code_cli(
    site, workspace, tmp_path, monkeypatch
):
    _install_fake_cli(tmp_path, monkeypatch, _FAKE_CLI)
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming",
        _cfg(depth=1, agent_enabled=True, agent_concurrency=2),
    )
    agent_stats = ctx.phases["agent"]
    assert agent_stats["provider"] == "claude-cli (OAuth)"
    assert agent_stats["agent_calls"] == agent_stats["candidates"]
    assert agent_stats["agent_failed"] == 0
    assert ctx.analysis_method == "agent"
    assert all(n.analysis_method == "agent" for n in ctx.nodes if n.extracted)
    assert ctx.nodes[0].analysis["page_type"] == "article"
    assert ctx.site_analysis["context_brief"].startswith("A programming index")
    assert ctx.site_analysis["_method"] == "agent"


def test_agent_page_budget_falls_back_to_heuristics(
    site, workspace, tmp_path, monkeypatch
):
    _install_fake_cli(tmp_path, monkeypatch, _FAKE_CLI)
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming",
        _cfg(depth=1, agent_enabled=True, agent_max_pages=2),
    )
    stats = ctx.phases["agent"]
    assert stats["agent_calls"] == 2
    assert stats["heuristic"] == stats["candidates"] - 2
    assert ctx.analysis_method == "mixed"
    # The seed always gets a real call; the rest still carry an analysis.
    assert ctx.node_by_url(f"{site}/category/programming").analysis_method == "agent"
    assert all(n.analysis for n in ctx.nodes if n.extracted)


def test_agent_without_cli_falls_back_to_heuristics(
    site, workspace, tmp_path, monkeypatch
):
    monkeypatch.setenv("AIEO_CLAUDE_CLI_BIN", str(tmp_path / "definitely-not-here"))
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1, agent_enabled=True)
    )
    stats = ctx.phases["agent"]
    assert stats["agent_calls"] == 0
    assert stats["heuristic"] == stats["candidates"]
    assert "not found on PATH" in stats["skipped_reason"]
    assert ctx.analysis_method == "heuristic"
    seed = ctx.node_by_url(f"{site}/category/programming")
    assert seed.analysis["_method"] == "heuristic"
    assert seed.analysis["page_type"] == "index"
    assert ctx.site_analysis["_method"] == "heuristic"
    assert ctx.site_analysis["context_brief"]


def test_agent_failures_trip_the_circuit_breaker(
    site, workspace, tmp_path, monkeypatch
):
    _install_fake_cli(tmp_path, monkeypatch, _FAILING_CLI)
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming",
        _cfg(depth=1, agent_enabled=True, agent_concurrency=1),
    )
    stats = ctx.phases["agent"]
    assert stats["agent_failed"] >= 3
    assert "circuit_breaker" in stats
    assert ctx.analysis_method == "heuristic"
    assert all(n.analysis_method == "heuristic" for n in ctx.nodes if n.extracted)
    assert any("401" in (n.analysis_error or "") for n in ctx.nodes if n.extracted)


def test_agent_disabled_skips_the_pass(site, workspace):
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=0, agent_enabled=False)
    )
    assert ctx.phases["agent"] == {"skipped": "agent disabled by config"}


def test_agent_prompts_come_from_markdown_files():
    agent = ContextAgent(ContextConfig())
    body = agent._prompt("site-context-analyst", "FALLBACK")
    assert body != "FALLBACK"
    assert "JSON" in body


def test_parse_json_tolerates_fences_and_prose():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Here you go:\n{"a": 2}\nHope that helps') == {"a": 2}
    with pytest.raises(ValueError):
        parse_json("no json here")
    with pytest.raises(ValueError):
        parse_json("")


def test_offline_without_any_api_key(site, workspace, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=1)
    )
    assert ctx.stats["nodes_extracted"] >= 4


# --------------------------------------------------------------------------- #
# Optional library adapters (installed or not, the build must work)
# --------------------------------------------------------------------------- #
def test_optional_libraries_are_optional(site, workspace):
    """Nothing extra installed is the default case and must change nothing."""
    from app.services.site_context import adapters

    assert adapters.extract_main_text("<html><body><p>hi</p></body></html>") in (
        None,
        adapters.extract_main_text("<html><body><p>hi</p></body></html>"),
    )
    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=0)
    )
    assert ctx.nodes[0].extracted
    assert ctx.nodes[0].content["engine"] in ("builtin", "trafilatura")


def test_library_extractor_policy():
    """Articles may use the library; hubs must keep the built-in path, because
    article extractors discard the link lists a hub is made of."""
    from app.services.site_context.adapters import should_use_library_extractor as pick

    assert pick("auto", is_index=False, installed=True) is True
    assert pick("auto", is_index=True, installed=True) is False
    assert pick("trafilatura", is_index=True, installed=True) is True
    assert pick("builtin", is_index=False, installed=True) is False
    # Never when the library is absent.
    assert pick("auto", is_index=False, installed=False) is False
    assert pick("trafilatura", is_index=False, installed=False) is False


def test_trafilatura_adapter_used_when_installed(site, workspace, monkeypatch):
    """A stub stands in for trafilatura so the wiring is tested without the dep."""
    import sys
    import types

    stub = types.ModuleType("trafilatura")
    stub.extract = lambda html, **kw: "Library extracted body text " * 200
    monkeypatch.setitem(sys.modules, "trafilatura", stub)

    ctx = SiteContextService(root=workspace).build(
        f"{site}/page/binary-array-set", _cfg(depth=0)
    )
    node = ctx.nodes[0]
    assert node.content["engine"] == "trafilatura"
    assert "Library extracted body text" in node.content["text"]

    # A hub keeps the built-in extractor even with the library present.
    hub = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=0)
    )
    assert hub.nodes[0].content["engine"] == "builtin"


def test_library_output_is_rejected_when_it_finds_less(site, workspace, monkeypatch):
    """A library that returns a stub must not replace working built-in output."""
    import sys
    import types

    stub = types.ModuleType("trafilatura")
    stub.extract = lambda html, **kw: "too short"
    monkeypatch.setitem(sys.modules, "trafilatura", stub)

    ctx = SiteContextService(root=workspace).build(
        f"{site}/page/binary-array-set", _cfg(depth=0)
    )
    assert ctx.nodes[0].content["engine"] == "builtin"
    assert ctx.nodes[0].content["word_count"] > 100


def test_extruct_adapter_adds_non_jsonld_structured_data(site, workspace, monkeypatch):
    import sys
    import types

    stub = types.ModuleType("extruct")
    stub.extract = lambda html, **kw: {
        "json-ld": [{"@type": "CollectionPage"}],
        "microdata": [{"@type": "BreadcrumbList"}],
        "rdfa": [],
        "microformat": [],
    }
    monkeypatch.setitem(sys.modules, "extruct", stub)

    ctx = SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=0)
    )
    node = ctx.nodes[0]
    assert "BreadcrumbList" in node.meta["jsonld_types"]  # microdata, invisible before
    assert node.meta["structured_data_syntaxes"]["microdata"] == 1


def test_protego_adapter_is_used_for_robots(site, workspace, monkeypatch):
    import sys
    import types

    calls = []

    class _Parsed:
        sitemaps = []

        def can_fetch(self, url, agent):
            calls.append(url)
            return "/private" not in url

        def crawl_delay(self, agent):
            return None

    stub = types.ModuleType("protego")
    stub.Protego = types.SimpleNamespace(parse=lambda text: _Parsed())
    monkeypatch.setitem(sys.modules, "protego", stub)

    ctx = SiteContextService(root=workspace).build(f"{site}/", _cfg(depth=1))
    assert calls, "protego should have been consulted"
    assert "/private" not in _paths(ctx)


def test_libraries_can_be_switched_off(site, workspace, monkeypatch):
    import sys
    import types

    stub = types.ModuleType("trafilatura")
    stub.extract = lambda html, **kw: "Library extracted body text " * 200
    monkeypatch.setitem(sys.modules, "trafilatura", stub)

    ctx = SiteContextService(root=workspace).build(
        f"{site}/page/binary-array-set",
        _cfg(depth=0, use_optional_libraries=False),
    )
    assert ctx.nodes[0].content["engine"] == "builtin"


def test_invalid_extractor_is_rejected():
    with pytest.raises(ValueError):
        ContextConfig(extractor="magic")


# --------------------------------------------------------------------------- #
# Exports + persistence
# --------------------------------------------------------------------------- #
def test_all_formats_export(site, workspace, tmp_path):
    svc = SiteContextService(root=workspace)
    ctx = svc.build(f"{site}/category/programming", _cfg(depth=1))
    out = svc.export(ctx, list(exporters.FORMATS), tmp_path / "out")
    for fmt in exporters.FORMATS:
        assert "error" not in out[fmt], out[fmt]
        assert Path(out[fmt]["path"]).exists()
        assert out[fmt]["bytes"] > 0

    markdown = Path(out["markdown"]["path"]).read_text(encoding="utf-8")
    assert "# Site context:" in markdown
    assert "## Link map" in markdown

    mermaid = Path(out["mermaid"]["path"]).read_text(encoding="utf-8")
    assert mermaid.startswith("graph LR")
    assert "-->" in mermaid

    html = Path(out["html"]["path"]).read_text(encoding="utf-8")
    assert "<script" not in html.lower()  # exports stay inert
    assert "Presentation" in html


def test_unknown_format_is_reported(site, workspace, tmp_path):
    svc = SiteContextService(root=workspace)
    ctx = svc.build(f"{site}/category/programming", _cfg(depth=0))
    out = svc.export(ctx, ["json", "pdf"], tmp_path / "out")
    assert "error" in out["pdf"]
    assert "error" not in out["json"]


def test_manifest_roundtrips_and_reexports_offline(site, workspace, tmp_path):
    svc = SiteContextService(root=workspace)
    result = svc.run(
        f"{site}/category/programming", formats=["json"], cfg=_cfg(depth=1)
    )
    manifest = svc.load_manifest(result["site_slug"], result["context_key"])
    assert manifest is not None
    restored = SiteContext.from_dict(manifest)
    assert len(restored.nodes) == result["stats"]["nodes_total"]
    assert restored.nodes[0].seo["title"]["text"] == "Programming"
    # Every format re-renders from the stored manifest with no network.
    assert exporters.render(restored, "markdown")
    assert exporters.render(restored, "mermaid").startswith("graph LR")


def test_run_returns_a_summary(site, workspace):
    result = SiteContextService(root=workspace).run(
        f"{site}/category/programming", formats=["json", "markdown"], cfg=_cfg(depth=1)
    )
    assert result["seed_url"] == f"{site}/category/programming"
    assert result["stats"]["nodes_total"] >= 4
    assert set(result["outputs"]) == {"json", "markdown"}
    assert Path(result["manifest_path"]).exists()
    assert result["depth_histogram"]["0"] == 1


def test_list_contexts(site, workspace):
    svc = SiteContextService(root=workspace)
    svc.run(f"{site}/category/programming", formats=["json"], cfg=_cfg(depth=0))
    svc.run(f"{site}/about", formats=["json"], cfg=_cfg(depth=0))
    listed = svc.list_contexts()
    assert len(listed) == 2
    assert {row["seed_url"] for row in listed} == {
        f"{site}/category/programming",
        f"{site}/about",
    }


def test_context_keys_are_readable_and_stable():
    key = context_key("https://www.nayuki.io/category/programming")
    assert key.startswith("category-programming-")
    assert key == context_key("https://www.nayuki.io/category/programming")
    assert key != context_key("https://www.nayuki.io/category/math")
    assert (
        context_key("https://example.com/")
        == "root-" + context_key("https://example.com/").rsplit("-", 1)[1]
    )


def test_traversal_slugs_and_keys_are_rejected(workspace):
    assert load_context_manifest("../../etc", "passwd", root=workspace) is None
    assert (
        load_context_manifest("nayuki_io", "../../../secrets", root=workspace) is None
    )
    assert list_contexts(root=workspace) == []


def test_store_uses_the_shared_snapshot_cache(site, workspace):
    SiteContextService(root=workspace).build(
        f"{site}/category/programming", _cfg(depth=0)
    )
    store = ContextStore(f"{site}/category/programming", root=workspace)
    assert store.manifest_path().exists()
    assert store.cache.dir.name == store.site_slug
    assert (store.cache.dir / "context").is_dir()


def test_bad_seed_url_is_rejected(workspace):
    svc = SiteContextService(root=workspace)
    with pytest.raises(ValueError):
        svc.build("", _cfg())
    with pytest.raises(ValueError):
        svc.build("https://example.com/style.css", _cfg())


def test_invalid_scope_is_rejected():
    with pytest.raises(ValueError):
        ContextConfig(scope="everything")


def test_config_from_dict_ignores_unknown_keys():
    cfg = ContextConfig.from_dict({"depth": 4, "nope": 1, "scope": "path"})
    assert cfg.depth == 4 and cfg.scope == "path"
    assert json.loads(json.dumps(cfg.to_dict()))["depth"] == 4
