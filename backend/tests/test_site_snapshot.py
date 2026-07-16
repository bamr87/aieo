"""Offline tests for the site snapshot feature.

The whole suite runs with no network egress and no API key: a tiny Jekyll-like
fixture site is served from 127.0.0.1 by ``http.server`` in a background thread.
Only the lean dependency set (httpx + beautifulsoup4 + markdown + html2text) is
required.
"""

from __future__ import annotations

import json
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.services.content_parser import ContentParser
from app.services.site_snapshot import CrawlConfig, SiteSnapshot, SiteSnapshotService
from app.services.site_snapshot import exporters, fetcher
from app.services.site_snapshot.discovery import normalize_url, safe_xml_parse
from app.services.site_snapshot.fetcher import BlockedHostError, guard_host
from app.services.site_snapshot.snapshot_cache import InvalidSlugError, SnapshotCache


def _write_site(root: Path, base: str) -> None:
    (root / "index.html").write_text(
        f"""<!DOCTYPE html><html lang="en"><head>
<title>Home</title><meta name="description" content="The home page.">
<meta name="generator" content="Jekyll v4.3.2"><link rel="canonical" href="{base}/">
</head><body><h1>Welcome</h1><p>Hello world, this is the home page with words.</p>
<a href="/posts/a/">A</a> <a href="/posts/b.html">B</a>
<a href="https://external.example.com/x">ext</a>
<img src="/assets/logo.png" alt="logo"></body></html>""",
        encoding="utf-8",
    )
    posts = root / "posts"
    posts.mkdir(exist_ok=True)
    (posts / "a.html").write_text(
        """<html><head><title>Post A</title><meta name="author" content="Amr">
<meta property="article:published_time" content="2026-01-02"></head>
<body><h1>Post A</h1><h2>Sec</h2><p>Body of post A here.</p>
<table><tr><th>k</th><th>v</th></tr><tr><td>1</td><td>2</td></tr></table>
<a href="/">home</a></body></html>""",
        encoding="utf-8",
    )
    (posts / "a").mkdir(exist_ok=True)
    (posts / "a" / "index.html").write_text(
        (posts / "a.html").read_text(), encoding="utf-8"
    )
    (posts / "b.html").write_text(
        "<html><head><title>Post B</title></head><body><h1>Post B</h1>"
        '<p>Body of post B.</p><a href="/posts/a/">A</a></body></html>',
        encoding="utf-8",
    )
    priv = root / "private"
    priv.mkdir(exist_ok=True)
    (priv / "secret.html").write_text(
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
<url><loc>{base}/</loc><lastmod>2026-01-01T00:00:00+00:00</lastmod></url>
<url><loc>{base}/posts/a/</loc></url>
<url><loc>{base}/posts/b.html</loc></url>
<url><loc>{base}/private/secret.html</loc></url>
</urlset>""",
        encoding="utf-8",
    )
    (root / "feed.xml").write_text(
        f'<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom">'
        f'<entry><link href="{base}/posts/a/" rel="alternate"/></entry></feed>',
        encoding="utf-8",
    )


@pytest.fixture
def site(tmp_path, monkeypatch):
    """Serve a fixture Jekyll site from 127.0.0.1; yield (base_url, site_dir)."""
    monkeypatch.setenv("AIEO_SNAPSHOT_ALLOW_PRIVATE", "1")
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    base = f"http://127.0.0.1:{port}"
    _write_site(site_dir, base)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.15)
    try:
        yield base, site_dir
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture
def workspace(tmp_path):
    return tmp_path / "ws"


def _cfg(**kw):
    kw.setdefault("delay_seconds", 0.0)
    return CrawlConfig(**kw)


# --------------------------------------------------------------------------- #
# URL normalization
# --------------------------------------------------------------------------- #
def test_normalize_url_collapses_variants():
    base = "https://ex.com/"
    a = normalize_url("/foo", base)
    b = normalize_url("/foo/index.html", base)
    c = normalize_url("/foo#frag", base)
    d = normalize_url("/foo//", base)
    assert a == normalize_url("/foo", base)  # idempotent
    assert b == "https://ex.com/foo/"
    assert c == a
    assert d == "https://ex.com/foo/"
    assert normalize_url("HTTPS://EX.COM/Bar", base) == "https://ex.com/Bar"


def test_normalize_url_drops_assets_and_schemes():
    base = "https://ex.com/"
    assert normalize_url("/img/logo.png", base) is None
    assert normalize_url("/style.css", base) is None
    assert normalize_url("mailto:x@y.com", base) is None
    assert normalize_url("javascript:void(0)", base) is None


# --------------------------------------------------------------------------- #
# Discovery + robots
# --------------------------------------------------------------------------- #
def test_discovery_prefers_sitemap_and_respects_robots(site, workspace):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    snap = svc.crawl(base, _cfg())
    urls = [p.url for p in snap.pages]
    assert snap.discovery["source"] == "sitemap"
    assert snap.discovery["sitemap_urls"] == 4
    # robots Disallow: /private/ keeps the secret page out.
    assert not any("secret" in u for u in urls)
    assert snap.stats["robots_skipped"] == 1
    assert snap.is_jekyll is True
    assert snap.site_generator == "Jekyll v4.3.2"


def test_no_robots_includes_disallowed(site, workspace):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    snap = svc.crawl(base, _cfg(respect_robots=False))
    assert any("secret" in p.url for p in snap.pages)


# --------------------------------------------------------------------------- #
# Caching / incremental re-runs
# --------------------------------------------------------------------------- #
def test_rerun_is_incremental_via_304(site, workspace):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    first = svc.crawl(base, _cfg())
    assert first.stats["pages_new"] == 3
    assert first.stats["pages_from_cache"] == 0

    second = svc.crawl(base, _cfg())
    assert second.stats["pages_total"] == 3
    assert second.stats["pages_from_cache"] == 3
    assert second.stats["pages_changed"] == 0
    assert second.stats["cache_hit_rate"] == 1.0


def test_changed_page_detected_on_rerun(site, workspace):
    base, site_dir = site
    svc = SiteSnapshotService(root=workspace)
    svc.crawl(base, _cfg())
    # Mutate one post; its mtime advances so the server serves a fresh 200.
    time.sleep(1.0)
    (site_dir / "posts" / "b.html").write_text(
        "<html><head><title>Post B v2</title></head><body><h1>Post B v2</h1>"
        "<p>Rewritten body with different content entirely.</p></body></html>",
        encoding="utf-8",
    )
    second = svc.crawl(base, _cfg())
    changed = [p for p in second.pages if p.changed and not p.from_cache]
    assert len(changed) == 1
    assert "b.html" in changed[0].url
    assert second.stats["pages_changed"] == 1


def test_no_cache_purges_and_refetches(site, workspace):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    svc.crawl(base, _cfg())
    fresh = svc.crawl(base, _cfg(use_cache=False))
    assert fresh.stats["pages_from_cache"] == 0


def test_refresh_bypasses_validators(site, workspace):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    svc.crawl(base, _cfg())
    refreshed = svc.crawl(base, _cfg(refresh=True))
    # Every page re-fetched (200, not served from cache) even though unchanged.
    assert refreshed.stats["pages_from_cache"] == 0


def test_stale_served_same_host_after_outage(site, workspace, monkeypatch):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    svc.crawl(base, _cfg())

    # Force every live fetch to error, with the cache already warm.
    err = fetcher.FetchResult(url="x", error="ConnectError: simulated outage")
    monkeypatch.setattr(
        fetcher.Fetcher, "fetch", lambda self, url, conditional=None: err
    )
    snap = svc.crawl(base, _cfg())
    assert all(p.stale for p in snap.pages if p.from_cache)
    assert snap.stats["pages_stale"] >= 1
    assert snap.degraded is True


# --------------------------------------------------------------------------- #
# Extraction parity + rollups
# --------------------------------------------------------------------------- #
def test_content_hash_matches_content_parser(site, workspace):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    snap = svc.crawl(base, _cfg())
    cache_dir = workspace / ".cache" / "snapshots" / snap.site_slug / "raw"
    import gzip

    parser = ContentParser()
    for page in snap.pages:
        body_file = cache_dir / f"{page.url_key}.body.gz"
        raw = gzip.decompress(body_file.read_bytes()).decode("utf-8")
        assert page.content_hash == parser._hash_content(raw)
        # word_count is over extracted text, not the raw HTML hash basis.
        assert page.word_count == len(page.text.split())


def test_rollups(site, workspace):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    snap = svc.crawl(base, _cfg())
    assert snap.totals["word_count"] == sum(p.word_count for p in snap.pages)
    domains = [d["domain"] for d in snap.outbound_domains]
    assert "external.example.com" in domains
    assert any(a["url"].endswith("logo.png") for a in snap.asset_inventory)
    assert snap.site_slug in snap.link_graph or snap.link_graph  # graph populated


# --------------------------------------------------------------------------- #
# Exporters
# --------------------------------------------------------------------------- #
def test_all_formats_single_file(site, workspace, tmp_path):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    result = svc.snapshot(
        base,
        formats=["text", "json", "markdown", "html", "pdf", "bundle"],
        cfg=_cfg(),
        out_dir=tmp_path / "out",
    )
    for fmt in ["text", "json", "markdown", "html", "pdf", "bundle"]:
        info = result["outputs"][fmt]
        assert "error" not in info, info
        assert Path(info["path"]).exists()
        assert info["bytes"] > 0

    html = Path(result["outputs"]["html"]["path"]).read_text(encoding="utf-8")
    assert "<script" not in html.lower()
    assert "stylesheet" not in html.lower()  # no external CSS link
    assert 'href="#' in html  # internal anchors for navigation


def test_json_roundtrip_reexport_offline(site, workspace):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    snap = svc.crawl(base, _cfg())
    manifest = json.loads(exporters.export_json(snap))
    reloaded = SiteSnapshot.from_dict(manifest)
    # Re-render every format from the reloaded manifest with no network.
    for fmt in exporters.FORMATS:
        data, _engine, _ = exporters.render(reloaded, fmt)
        assert data


def test_pdf_stdlib_is_structurally_valid():
    from app.services.site_snapshot import pdf_writer

    data = pdf_writer.render_text_pdf("Title", "para one\n\n" + ("word " * 500))
    assert data[:8] == b"%PDF-1.4"
    assert data.rstrip().endswith(b"%%EOF")
    # Validate the xref: every declared offset must point at "<n> 0 obj".
    start = data.rfind(b"startxref")
    xref_pos = int(data[start:].split(b"\n")[1].strip())
    xref = data[xref_pos:]
    lines = xref.split(b"\n")
    assert lines[0] == b"xref"
    count = int(lines[1].split()[1])
    for n in range(1, count):
        offset = int(lines[2 + n].split()[0])
        assert data[offset:].startswith(f"{n} 0 obj".encode())


def test_pdf_auto_falls_back_to_stdlib(site, workspace, monkeypatch):
    base, _ = site
    from app.services.site_snapshot import pdf_writer

    monkeypatch.setattr(pdf_writer, "try_reportlab", lambda *a, **k: None)
    monkeypatch.setattr(pdf_writer, "try_playwright", lambda *a, **k: None)
    svc = SiteSnapshotService(root=workspace)
    snap = svc.crawl(base, _cfg())
    data, engine = exporters.export_pdf(snap)
    assert engine == "stdlib"
    assert data[:8] == b"%PDF-1.4"


def test_unknown_format_errors(site, workspace):
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    snap = svc.crawl(base, _cfg())
    with pytest.raises(ValueError):
        exporters.render(snap, "doc")


# --------------------------------------------------------------------------- #
# SSRF guard
# --------------------------------------------------------------------------- #
def test_guard_blocks_private_hosts(monkeypatch):
    monkeypatch.delenv("AIEO_SNAPSHOT_ALLOW_PRIVATE", raising=False)
    for url in (
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1/",
        "http://localhost/",
        "http://[::1]/",
        "http://10.0.0.5/",
    ):
        with pytest.raises(BlockedHostError):
            guard_host(url)


def test_guard_allows_when_flagged(monkeypatch):
    monkeypatch.setenv("AIEO_SNAPSHOT_ALLOW_PRIVATE", "1")
    guard_host("http://127.0.0.1:8000/")  # must not raise


def test_offline_no_api_key(site, workspace, monkeypatch, tmp_path):
    """A full snapshot works with no OpenAI/Anthropic key configured."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    result = svc.snapshot(
        base, formats=["html", "json"], cfg=_cfg(), out_dir=tmp_path / "o"
    )
    assert result["stats"]["pages_total"] == 3


def test_main_content_extraction_strips_chrome():
    """The extractor records main content only, dropping nav/footer/TOC/cookie chrome."""
    from app.services.site_snapshot.extractor import PageExtractor
    from app.services.site_snapshot.model import PageRecord

    html = """<html><head><title>T</title></head><body>
      <header id="navbar"><nav><a href="/">Home</a><a href="/services/">Services</a></nav></header>
      <main><h1>Real Title</h1>
      <p>The actual unique article content lives here. It is deliberately long enough
      to clear the main-content selection threshold so the extractor anchors on the
      main element rather than falling back to the whole body. This sentence pads it
      well past two hundred characters of genuine article prose.</p>
      <nav class="toc"><a href="#x">jump to section</a></nav></main>
      <footer>Copyright 2026 footer boilerplate text</footer>
      <div class="cookie-consent-banner">We use cookies on this site</div></body></html>"""

    def run(strip):
        return PageExtractor().extract(
            normalized_url="https://e.com/p/",
            base_url="https://e.com/",
            final_url="https://e.com/p/",
            html=html,
            content_hash="x",
            discovery_source="seed",
            root_host="e.com",
            include_external=False,
            record=PageRecord(url="https://e.com/p/"),
            strip_boilerplate=strip,
        )

    rec = run(True)
    assert rec.content_root == "main"
    assert "actual unique article content" in rec.text
    assert "Services" not in rec.text  # nav dropped
    assert (
        "footer boilerplate" not in rec.text
    )  # footer dropped (body fallback not used, but main has no footer)
    assert "cookies" not in rec.text  # cookie banner dropped
    assert "jump to section" not in rec.text  # in-content TOC nav dropped

    full = run(False)
    assert full.content_root == "body"
    assert "Services" in full.text  # full-page mode keeps chrome


def test_guard_blocks_cgnat(monkeypatch):
    monkeypatch.delenv("AIEO_SNAPSHOT_ALLOW_PRIVATE", raising=False)
    with pytest.raises(BlockedHostError):
        guard_host("http://100.64.1.1/")  # RFC 6598 CGNAT, not is_global


# --------------------------------------------------------------------------- #
# Regression tests for the adversarial review findings
# --------------------------------------------------------------------------- #
def test_refresh_reports_no_new_or_changed_for_unchanged_site(site, workspace):
    """--refresh must not mislabel already-cached, unchanged pages as 'new'."""
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    svc.crawl(base, _cfg())
    refreshed = svc.crawl(base, _cfg(refresh=True))
    assert refreshed.stats["pages_from_cache"] == 0  # validators bypassed
    assert refreshed.stats["pages_new"] == 0
    assert refreshed.stats["pages_changed"] == 0


def test_refresh_still_serves_stale_on_outage(site, workspace, monkeypatch):
    """A refresh run must keep the stale-on-error fallback (cache not abandoned)."""
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    svc.crawl(base, _cfg())
    err = fetcher.FetchResult(url="x", error="ConnectError: outage")
    monkeypatch.setattr(fetcher.Fetcher, "fetch", lambda self, u, conditional=None: err)
    snap = svc.crawl(base, _cfg(refresh=True))
    assert snap.stats["pages_stale"] >= 1


def test_unchanged_200_skips_reparse_and_is_honest(site, workspace, monkeypatch):
    """A server that ignores conditionals (always 200) must NOT inflate
    cache_hit_rate, and unchanged pages must skip re-parsing (revalidated)."""
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    svc.crawl(base, _cfg())

    # Force every conditional GET to come back as a fresh 200 (no 304).
    real_fetch = fetcher.Fetcher.fetch

    def always_200(self, url, conditional=None):
        return real_fetch(self, url, None)

    monkeypatch.setattr(fetcher.Fetcher, "fetch", always_200)

    # Count extractor calls to prove re-parse is skipped on unchanged pages.
    from app.services.site_snapshot import extractor as extractor_mod

    calls = {"n": 0}
    real_extract = extractor_mod.PageExtractor.extract

    def counting_extract(self, **kwargs):
        calls["n"] += 1
        return real_extract(self, **kwargs)

    monkeypatch.setattr(extractor_mod.PageExtractor, "extract", counting_extract)

    snap = svc.crawl(base, _cfg())
    assert snap.stats["pages_from_cache"] == 0  # everything was re-downloaded
    assert snap.stats["pages_revalidated"] == snap.stats["pages_total"]
    assert snap.stats["cache_hit_rate"] == 0.0
    assert calls["n"] == 0  # no page was re-parsed


def test_truncated_page_does_not_flap(workspace, monkeypatch):
    """A >max_bytes page must settle (be cached + recognized), not flap 'new'/'changed'."""
    big = (
        "<html><head><title>Big</title></head><body><h1>Big</h1><p>"
        + ("word " * 5000)
        + "</p></body></html>"
    )

    def fake_fetch(self, url, conditional=None):
        return fetcher.FetchResult(
            url=url,
            final_url=url,
            status=200,
            headers={},
            text=big,
            content_type="text/html",
            truncated=True,
        )

    monkeypatch.setattr(fetcher.Fetcher, "fetch", fake_fetch)
    svc = SiteSnapshotService(root=workspace)
    cfg = _cfg(max_bytes_per_page=200)
    r1 = svc.crawl("https://trunc.example.com", cfg)
    r2 = svc.crawl("https://trunc.example.com", cfg)
    assert r1.pages[0].truncated is True
    assert r1.stats["pages_new"] == 1
    # Second run must recognize the page (not "new" again) and not flap "changed".
    assert r2.stats["pages_new"] == 0
    assert r2.stats["pages_changed"] == 0


def test_invalid_slug_blocked():
    for bad in ("..", "../etc", "a/b", "%2e%2e", ""):
        with pytest.raises(InvalidSlugError):
            SnapshotCache(bad)


def test_load_manifest_rejects_traversal_slug(workspace):
    svc = SiteSnapshotService(root=workspace)
    assert svc.load_manifest("..") is None
    assert svc.load_manifest("../../etc") is None


def test_safe_xml_parse_rejects_entity_bomb():
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        '<!ENTITY lol2 "&lol;&lol;">]><urlset><url><loc>x</loc></url></urlset>'
    )
    assert safe_xml_parse(bomb) is None  # DOCTYPE/ENTITY refused
    ok = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
    assert safe_xml_parse(ok) is not None


def test_html_export_is_inert(site, workspace, tmp_path):
    """Rendered page HTML must drop scripts/iframes/on* handlers/js: URLs."""
    base, _ = site
    svc = SiteSnapshotService(root=workspace)
    snap = svc.crawl(base, _cfg())
    # Inject hostile content into a page body and re-export.
    snap.pages[0].markdown = (
        "Hello <script>alert(1)</script> "
        '<img src=x onerror="alert(1)"> '
        '<a href="javascript:alert(1)">x</a> '
        "<iframe src=//evil></iframe>"
    )
    html = exporters.export_html(snap)
    low = html.lower()
    assert "<script" not in low
    assert "<iframe" not in low
    assert "onerror" not in low
    assert "javascript:" not in low


def test_html_export_survives_null_timestamps():
    """export_html must not crash on a round-tripped manifest with null timestamps."""
    manifest = {
        "base_url": "https://example.com",
        "created_at": None,
        "completed_at": None,
        "site_summary": None,
        "pages": [],
    }
    site = SiteSnapshot.from_dict(manifest)
    assert exporters.export_html(site)  # no AttributeError


def test_include_assets_inlines_relative_image(site, workspace, tmp_path, monkeypatch):
    """--include-assets must inline a Jekyll page's RELATIVE image src as a data URI."""
    base, _ = site
    # Serve a 1x1 PNG for any image fetch.
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    monkeypatch.setattr(
        fetcher.Fetcher,
        "fetch_bytes",
        lambda self, url, max_bytes=None: (png, "image/png", None),
    )
    svc = SiteSnapshotService(root=workspace)
    result = svc.snapshot(
        base, formats=["html"], cfg=_cfg(include_assets=True), out_dir=tmp_path / "o"
    )
    html = Path(result["outputs"]["html"]["path"]).read_text(encoding="utf-8")
    # The home page references /assets/logo.png (relative) — it must be inlined.
    assert "data:image/png;base64," in html
    assert "/assets/logo.png" not in html
