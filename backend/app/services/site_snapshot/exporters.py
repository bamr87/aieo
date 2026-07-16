"""Single-file exporters for a :class:`SiteSnapshot`.

Every format is rendered from the one in-memory model so they stay consistent:
``text`` (grep/LLM-friendly), ``json`` (lossless manifest), ``markdown`` (a
single "book"), ``html`` (a self-contained navigable file), ``pdf`` (stdlib
floor + optional engines), and ``bundle`` (a .zip package of the lot — the
"package" form of the deliverable).
"""

from __future__ import annotations

import html as html_lib
import io
import json
import re
import textwrap
import zipfile
from string import Template
from typing import Any, Dict, List, Optional

from . import pdf_writer
from .model import SiteSnapshot

FORMATS = ["text", "json", "markdown", "html", "pdf", "bundle"]
_EXT = {
    "text": ".txt",
    "json": ".json",
    "markdown": ".md",
    "html": ".html",
    "pdf": ".pdf",
    "bundle": ".zip",
}


def extension_for(fmt: str) -> str:
    return _EXT.get(fmt, ".txt")


def _content_pages(site: SiteSnapshot) -> List:
    return list(site.pages)


# --------------------------------------------------------------------------- #
# JSON
# --------------------------------------------------------------------------- #
def export_json(site: SiteSnapshot) -> str:
    return json.dumps(site.to_dict(), indent=2, ensure_ascii=False, default=str)


# --------------------------------------------------------------------------- #
# Plain text
# --------------------------------------------------------------------------- #
def export_text(site: SiteSnapshot, *, full_text: bool = True) -> str:
    out = io.StringIO()
    w = out.write
    rule = "=" * 78
    w(f"{rule}\nSITE SNAPSHOT: {site.base_url}\n{rule}\n")
    w(f"Generated : {site.completed_at or site.created_at}\n")
    w(f"Generator : {site.site_generator or 'unknown'} (jekyll={site.is_jekyll})\n")
    stats = site.stats or {}
    w(
        "Pages     : {total} ({ok} ok, {cache} cached, {changed} changed, "
        "{new} new, {err} error{deg})\n".format(
            total=stats.get("pages_total", 0),
            ok=stats.get("pages_ok", 0),
            cache=stats.get("pages_from_cache", 0),
            changed=stats.get("pages_changed", 0),
            new=stats.get("pages_new", 0),
            err=stats.get("pages_error", 0),
            deg=" [DEGRADED]" if site.degraded else "",
        )
    )
    totals = site.totals or {}
    w(
        "Totals    : {words} words, ~{rt} min read, {il} internal / {el} external "
        "links, {img} images\n".format(
            words=totals.get("word_count", 0),
            rt=totals.get("reading_time_min", 0),
            il=totals.get("internal_links", 0),
            el=totals.get("external_links", 0),
            img=totals.get("images", 0),
        )
    )
    if site.site_summary:
        w("\nSummary:\n")
        w(textwrap.fill(site.site_summary, width=78) + "\n")

    w(f"\n{'-' * 78}\nTABLE OF CONTENTS\n{'-' * 78}\n")
    for i, page in enumerate(_content_pages(site), 1):
        flag = " [soft-404]" if page.is_soft_404 else (" [error]" if page.error else "")
        w(f"{i:>3}. {page.title or page.path or page.url}{flag}\n")
        w(f"     {page.url}  ({page.word_count} words, ~{page.reading_time_min} min)\n")

    for page in _content_pages(site):
        w(f"\n{rule}\n{page.title or page.url}\n{rule}\n")
        w(f"URL        : {page.url}\n")
        if page.final_url and page.final_url != page.url:
            w(f"Final URL  : {page.final_url}\n")
        w(f"Source     : {page.discovery_source}   Status: {page.status}   ")
        w(f"Cached: {page.from_cache}   Changed: {page.changed}\n")
        if page.date:
            w(f"Date       : {page.date}\n")
        if page.author:
            w(f"Author     : {page.author}\n")
        if page.tags:
            w(f"Tags       : {', '.join(page.tags)}\n")
        if page.error:
            w(f"ERROR      : {page.error}\n")
        if page.description:
            w(f"\n{textwrap.fill(page.description, width=78)}\n")
        if page.headers:
            w("\nOutline:\n")
            for h in page.headers:
                w(f"  {'  ' * (h['level'] - 1)}- {h['text']}\n")
        if full_text and page.text:
            w("\n" + textwrap.fill(page.text, width=78) + "\n")

    if site.errors:
        w(f"\n{rule}\nERRORS\n{rule}\n")
        for err in site.errors:
            w(f"- {err.get('url')}: {err.get('error')} (status {err.get('status')})\n")
    return out.getvalue()


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #
def export_markdown(site: SiteSnapshot) -> str:
    lines: List[str] = []
    stats = site.stats or {}
    totals = site.totals or {}
    lines += [
        "---",
        f"title: Site Snapshot — {site.base_url}",
        f"base_url: {site.base_url}",
        f"generated: {site.completed_at or site.created_at}",
        f"is_jekyll: {site.is_jekyll}",
        f"pages: {stats.get('pages_total', 0)}",
        f"words: {totals.get('word_count', 0)}",
        "---",
        "",
        f"# Site Snapshot — {site.base_url}",
        "",
    ]
    if site.site_summary:
        lines += [site.site_summary, ""]
    lines += ["## Contents", ""]
    for page in _content_pages(site):
        title = page.title or page.path or page.url
        lines.append(f"- [{title}](#{page.slug}) — {page.word_count} words")
    lines.append("")

    for page in _content_pages(site):
        lines += [f'<a id="{page.slug}"></a>', "", f"## {page.title or page.url}", ""]
        meta = [f"**URL:** {page.url}"]
        if page.date:
            meta.append(f"**Date:** {page.date}")
        if page.author:
            meta.append(f"**Author:** {page.author}")
        meta.append(f"**Words:** {page.word_count} (~{page.reading_time_min} min)")
        lines += ["  ".join(meta), ""]
        if page.tags:
            lines += [f"_Tags: {', '.join(page.tags)}_", ""]
        if page.error:
            lines += [f"> **Error:** {page.error}", ""]
        if page.markdown:
            lines += [page.markdown.strip(), ""]
        elif page.description:
            lines += [page.description, ""]
        lines += ["[↑ Contents](#contents)", "", "---", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# HTML (self-contained single file)
# --------------------------------------------------------------------------- #
_HTML_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="aieo-site-snapshot">
<title>Site Snapshot — $base_url</title>
<style>
:root{--fg:#1a1a1a;--muted:#666;--accent:#0a58ca;--border:#e2e2e2;--bg:#fff;}
*{box-sizing:border-box;}
body{margin:0;font:16px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--fg);background:var(--bg);}
#layout{display:flex;min-height:100vh;}
nav{width:300px;flex:0 0 300px;border-right:1px solid var(--border);padding:1rem;position:sticky;top:0;height:100vh;overflow:auto;background:#fafafa;}
nav h1{font-size:1rem;margin:.2rem 0 1rem;}
nav a{display:block;color:var(--accent);text-decoration:none;padding:.15rem 0;font-size:.9rem;}
nav a:hover{text-decoration:underline;}
nav .group{font-weight:600;color:var(--muted);margin-top:.8rem;text-transform:uppercase;font-size:.72rem;letter-spacing:.04em;}
main{flex:1;padding:2rem 3rem;max-width:60rem;overflow:auto;}
section{border-bottom:1px solid var(--border);padding-bottom:2rem;margin-bottom:2rem;}
section h2{margin-bottom:.2rem;}
.meta{color:var(--muted);font-size:.85rem;margin-bottom:1rem;}
.meta a{color:var(--accent);}
.stats{display:flex;flex-wrap:wrap;gap:1rem;margin:1rem 0;}
.stat{background:#f3f4f6;border-radius:8px;padding:.6rem 1rem;font-size:.85rem;}
.stat b{display:block;font-size:1.3rem;}
table{border-collapse:collapse;}td,th{border:1px solid var(--border);padding:.3rem .6rem;}
pre{background:#f6f8fa;padding:.8rem;overflow:auto;border-radius:6px;}
img{max-width:100%;height:auto;}
.toplink{font-size:.8rem;}
.badge{display:inline-block;background:#fde68a;color:#92400e;border-radius:4px;padding:0 .4rem;font-size:.7rem;}
</style></head>
<body><div id="layout">
<nav>
<h1>$base_url</h1>
<a href="#overview">Overview</a>
$nav
</nav>
<main>
<section id="overview">
<h2>Site Snapshot</h2>
<div class="meta">$base_url · generated $generated · jekyll=$is_jekyll</div>
<div class="stats">$stat_cards</div>
$summary
</section>
$sections
</main>
</div></body></html>
"""
)


_ACTIVE_TAGS = {"script", "iframe", "object", "embed", "form", "link", "meta", "base"}
_ACTIVE_URL_RE = re.compile(
    r"^\s*(?:javascript|vbscript|data:text/html)", re.IGNORECASE
)


def _sanitize_html(
    html: str,
    *,
    base_url: Optional[str] = None,
    assets_map: Optional[Dict[str, str]] = None,
) -> str:
    """Make rendered page HTML inert: drop active tags, on* handlers, and
    javascript:/data:text/html URLs. Also absolutize ``<img src>`` against
    ``base_url`` and inline any matching asset as a data URI (so a Jekyll page's
    relative image paths resolve / become offline). Uses BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
    except Exception:
        # No bs4 (lean env): fall back to escaping everything — safe, if ugly.
        return "<pre>" + html_lib.escape(html) + "</pre>"
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(_ACTIVE_TAGS):
        tag.decompose()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith("on"):
                del tag[attr]
        for attr in ("href", "src"):
            val = tag.get(attr)
            if isinstance(val, str) and _ACTIVE_URL_RE.match(val):
                tag[attr] = "#"
    if base_url:
        for img in soup.find_all("img"):
            src = img.get("src")
            if not isinstance(src, str) or src.startswith("data:"):
                continue
            absolute = urljoin(base_url, src)
            img["src"] = (assets_map or {}).get(absolute, absolute)
    return str(soup)


def _render_page_html(
    markdown_text: str,
    *,
    base_url: Optional[str] = None,
    assets_map: Optional[Dict[str, str]] = None,
) -> str:
    try:
        import markdown

        body = markdown.markdown(
            markdown_text or "", extensions=["tables", "fenced_code"]
        )
    except Exception:
        body = "<pre>" + html_lib.escape(markdown_text or "") + "</pre>"
    return _sanitize_html(body, base_url=base_url, assets_map=assets_map)


def export_html(site: SiteSnapshot, assets_map: Optional[Dict[str, str]] = None) -> str:
    pages = _content_pages(site)
    # Sidebar grouped by the first path segment.
    groups: Dict[str, List] = {}
    for page in pages:
        seg = (page.path or "/").strip("/").split("/", 1)[0] or "home"
        groups.setdefault(seg, []).append(page)
    nav_parts: List[str] = []
    for group in sorted(groups):
        nav_parts.append(f'<div class="group">{html_lib.escape(group)}</div>')
        for page in groups[group]:
            title = html_lib.escape(page.title or page.path or page.url)
            badge = ' <span class="badge">404?</span>' if page.is_soft_404 else ""
            nav_parts.append(f'<a href="#{page.slug}">{title}{badge}</a>')

    stats = site.stats or {}
    totals = site.totals or {}
    stat_cards = "".join(
        f'<div class="stat"><b>{v}</b>{k}</div>'
        for k, v in [
            ("pages", stats.get("pages_total", 0)),
            ("words", totals.get("word_count", 0)),
            ("~min read", totals.get("reading_time_min", 0)),
            ("ext links", totals.get("external_links", 0)),
            ("images", totals.get("images", 0)),
            ("cached", stats.get("pages_from_cache", 0)),
        ]
    )

    sections: List[str] = []
    for page in pages:
        page_base = page.final_url or page.url
        if page.markdown:
            body = _render_page_html(
                page.markdown, base_url=page_base, assets_map=assets_map
            )
        else:
            # No body: escape the (untrusted) meta description rather than render it.
            body = f"<p>{html_lib.escape(page.description or '')}</p>"
        meta_bits = [
            f'<a href="{html_lib.escape(page.url)}">{html_lib.escape(page.url)}</a>'
        ]
        if page.date:
            meta_bits.append(html_lib.escape(str(page.date)))
        meta_bits.append(f"{page.word_count} words · ~{page.reading_time_min} min")
        if page.from_cache:
            meta_bits.append("cached")
        err = (
            f'<p style="color:#b91c1c"><b>Error:</b> {html_lib.escape(page.error)}</p>'
            if page.error
            else ""
        )
        sections.append(
            f'<section id="{page.slug}">'
            f"<h2>{html_lib.escape(page.title or page.url)}</h2>"
            f'<div class="meta">{" · ".join(meta_bits)}</div>'
            f"{err}{body}"
            f'<p class="toplink"><a href="#overview">↑ overview</a></p>'
            f"</section>"
        )

    summary = (
        f"<p>{html_lib.escape(site.site_summary)}</p>" if site.site_summary else ""
    )
    return _HTML_TEMPLATE.substitute(
        base_url=html_lib.escape(str(site.base_url or "")),
        generated=html_lib.escape(str(site.completed_at or site.created_at or "")),
        is_jekyll=str(site.is_jekyll),
        nav="\n".join(nav_parts),
        stat_cards=stat_cards,
        summary=summary,
        sections="\n".join(sections),
    )


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def export_pdf(site: SiteSnapshot, *, engine: str = "auto") -> tuple[bytes, str]:
    """Return (pdf_bytes, engine_used). Never raises; always returns valid bytes."""
    title = f"Site Snapshot — {site.base_url}"
    text = export_text(site, full_text=False)
    if engine in ("auto", "reportlab"):
        data = pdf_writer.try_reportlab(title, text)
        if data:
            return data, "reportlab"
        if engine == "reportlab":
            pass  # fall through to stdlib
    if engine in ("auto", "playwright"):
        data = pdf_writer.try_playwright(export_html(site))
        if data:
            return data, "playwright"
    return pdf_writer.render_text_pdf(title, text), "stdlib"


# --------------------------------------------------------------------------- #
# Bundle (zip package)
# --------------------------------------------------------------------------- #
def export_bundle(
    site: SiteSnapshot,
    *,
    formats: Optional[List[str]] = None,
    assets_map: Optional[Dict[str, str]] = None,
) -> bytes:
    """A .zip 'package': the snapshot rendered in several text formats + manifest."""
    formats = formats or ["html", "markdown", "json", "text"]
    slug = site.site_slug or "site"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if "json" in formats:
            zf.writestr(f"{slug}/manifest.json", export_json(site))
        if "html" in formats:
            zf.writestr(f"{slug}/index.html", export_html(site, assets_map))
        if "markdown" in formats:
            zf.writestr(f"{slug}/{slug}.md", export_markdown(site))
        if "text" in formats:
            zf.writestr(f"{slug}/{slug}.txt", export_text(site))
        if "pdf" in formats:
            data, _ = export_pdf(site)
            zf.writestr(f"{slug}/{slug}.pdf", data)
        readme = (
            f"AIEO Site Snapshot of {site.base_url}\n"
            f"Generated: {site.completed_at or site.created_at}\n"
            f"Pages: {(site.stats or {}).get('pages_total', 0)}\n\n"
            "Open index.html in a browser for the navigable offline view.\n"
        )
        zf.writestr(f"{slug}/README.txt", readme)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
def render(site: SiteSnapshot, fmt: str, **kwargs) -> tuple[bytes, Optional[str], bool]:
    """Render one format. Returns (data_bytes, engine, is_text)."""
    if fmt == "json":
        return export_json(site).encode("utf-8"), None, True
    if fmt == "text":
        return export_text(site).encode("utf-8"), None, True
    if fmt == "markdown":
        return export_markdown(site).encode("utf-8"), None, True
    if fmt == "html":
        return export_html(site, kwargs.get("assets_map")).encode("utf-8"), None, True
    if fmt == "pdf":
        data, engine = export_pdf(site, engine=kwargs.get("engine", "auto"))
        return data, engine, False
    if fmt == "bundle":
        return export_bundle(site, assets_map=kwargs.get("assets_map")), None, False
    raise ValueError(f"Unknown format: {fmt!r}. Choose from {FORMATS}.")


def write_export(site: SiteSnapshot, fmt: str, out_path, **kwargs) -> Dict[str, Any]:
    from pathlib import Path

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data, engine, _is_text = render(site, fmt, **kwargs)
    out_path.write_bytes(data)
    info: Dict[str, Any] = {
        "format": fmt,
        "path": str(out_path),
        "bytes": len(data),
        "single_file": True,
    }
    if engine:
        info["engine"] = engine
    return info
