"""Single-file exporters for a :class:`SiteContext`.

Every format renders from the one in-memory dataset so they stay consistent:
``json`` (the lossless dataset — the thing you feed another tool), ``markdown``
(a readable context brief), ``html`` (a self-contained, inert review page) and
``mermaid`` (the link map as a graph you can paste into any Mermaid renderer).
"""

from __future__ import annotations

import html as html_lib
import io
import json
import re
from string import Template
from typing import Any, Dict

from .model import SiteContext

FORMATS = ["json", "markdown", "html", "mermaid"]
_EXT = {"json": ".json", "markdown": ".md", "html": ".html", "mermaid": ".mmd"}
_ID_RE = re.compile(r"[^A-Za-z0-9]+")


def extension_for(fmt: str) -> str:
    return _EXT.get(fmt, ".txt")


# --------------------------------------------------------------------------- #
# JSON
# --------------------------------------------------------------------------- #
def export_json(ctx: SiteContext) -> str:
    return json.dumps(ctx.to_dict(), indent=2, ensure_ascii=False, default=str)


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #
def export_markdown(ctx: SiteContext) -> str:
    out = io.StringIO()
    w = out.write
    stats = ctx.stats or {}
    analysis = ctx.site_analysis or {}

    w(f"# Site context: {ctx.seed_url}\n\n")
    w(f"- **Seed**: {ctx.seed_url}\n")
    w(
        f"- **Scope**: {(ctx.config or {}).get('scope')} · depth {(ctx.config or {}).get('depth')}\n"
    )
    w(f"- **Built**: {ctx.completed_at or ctx.created_at}\n")
    w(
        f"- **Pages**: {stats.get('nodes_total', 0)} mapped, {stats.get('nodes_extracted', 0)} extracted\n"
    )
    w(f"- **Analysis**: {ctx.analysis_method}")
    agent_stats = (ctx.phases or {}).get("agent", {})
    if agent_stats.get("agent_calls"):
        w(
            f" ({agent_stats.get('agent_ok', 0)}/{agent_stats['agent_calls']} agent calls ok)"
        )
    w("\n\n")

    if analysis.get("context_brief"):
        w("## Context brief\n\n")
        w(f"{analysis['context_brief']}\n\n")

    if analysis.get("site_purpose"):
        w("## Site\n\n")
        w(f"- **Purpose**: {analysis.get('site_purpose')}\n")
        if analysis.get("audience"):
            w(f"- **Audience**: {analysis['audience']}\n")
        ia = analysis.get("information_architecture") or {}
        if ia:
            w(
                f"- **Architecture**: {ia.get('pattern')} — {ia.get('depth_assessment', '')}\n"
            )
        w("\n")

    taxonomy = analysis.get("content_taxonomy") or []
    if taxonomy:
        w("## Content clusters\n\n")
        for cluster in taxonomy:
            w(f"### {cluster.get('cluster', 'cluster')}\n\n")
            if cluster.get("theme"):
                w(f"{cluster['theme']}\n\n")
            for url in (cluster.get("pages") or [])[:12]:
                w(f"- {url}\n")
            w("\n")

    w("## Link map\n\n")
    w("| Depth | Pages |\n| --- | --- |\n")
    for depth, count in sorted(
        (ctx.depth_histogram or {}).items(), key=lambda kv: int(kv[0])
    ):
        w(f"| {depth} | {count} |\n")
    w("\n")
    if ctx.hubs:
        w("**Hubs** (most linked-to):\n\n")
        for hub in ctx.hubs[:10]:
            w(
                f"- [{hub.get('title') or hub['url']}]({hub['url']}) — in {hub.get('in_degree', 0)}, out {hub.get('out_degree', 0)}\n"
            )
        w("\n")
    if ctx.orphans:
        w(f"**Orphans** ({len(ctx.orphans)}): " + ", ".join(ctx.orphans[:10]) + "\n\n")

    style = ctx.style_profile or {}
    anim = ctx.animation_profile or {}
    if style or anim:
        w("## Presentation\n\n")
        if style.get("palette"):
            w(
                "- **Palette**: "
                + ", ".join(c["color"] for c in style["palette"][:10])
                + "\n"
            )
        if style.get("font_families"):
            w("- **Type**: " + ", ".join(style["font_families"][:6]) + "\n")
        if style.get("frameworks") or style.get("js_frameworks"):
            w(
                "- **Frameworks**: "
                + ", ".join(
                    (style.get("frameworks") or []) + (style.get("js_frameworks") or [])
                )
                + "\n"
            )
        if style.get("breakpoints"):
            w("- **Breakpoints**: " + ", ".join(style["breakpoints"]) + "\n")
        if anim.get("summary"):
            w(f"- **Motion**: {anim['summary']}\n")
        w("\n")

    inter = ctx.interactivity_profile or {}
    if inter.get("interactive_pages"):
        w("## Interactive surface\n\n")
        w(f"{inter['summary']}\n\n")
        types = ", ".join(
            f"{n}x {k}" for k, n in list(inter["control_types"].items())[:8]
        )
        if types:
            w(f"- **Controls**: {types}\n")
        if inter.get("file_upload_pages"):
            w(f"- **File-processing tools**: {inter['file_upload_pages']}\n")
        if inter.get("progressive_enhancement_pages"):
            w(
                f"- **Need JS to reveal the demo**: "
                f"{inter['progressive_enhancement_pages']}\n"
            )
        w("\n")
        for page in inter["pages"][:10]:
            label = page.get("title") or page["url"]
            w(f"- [{label}]({page['url']}) — {'; '.join(page['signals'][:2])}\n")
        w("\n")

    seo = ctx.seo_profile or {}
    if seo.get("pages_analyzed"):
        w("## SEO profile\n\n")
        sev = seo.get("severity_counts") or {}
        w(
            f"- **Issues**: {sev.get('high', 0)} high, {sev.get('medium', 0)} medium, {sev.get('low', 0)} low\n"
        )
        w(
            f"- **Indexable**: {seo.get('indexable_pages')} / {seo.get('pages_analyzed')}\n"
        )
        w(f"- **Avg words**: {seo.get('avg_word_count')}\n")
        if seo.get("schema_types"):
            w("- **Schema types**: " + ", ".join(list(seo["schema_types"])[:8]) + "\n")
        top = list((seo.get("issue_counts") or {}).items())[:8]
        if top:
            w("\n| Issue | Pages |\n| --- | --- |\n")
            for code, count in top:
                w(f"| {code} | {count} |\n")
        w("\n")
        posture = analysis.get("seo_posture") or {}
        for action in (posture.get("priority_actions") or [])[:5]:
            w(f"- [ ] {action}\n")
        if posture.get("priority_actions"):
            w("\n")

    if ctx.external_references:
        w("## Outbound references\n\n")
        for ref in ctx.external_references[:15]:
            w(f"- **{ref['domain']}** ×{ref['count']}\n")
        w("\n")

    w("## Pages\n\n")
    for node in sorted(ctx.nodes, key=lambda n: (n.depth, n.url)):
        w(f"### [L{node.depth}] {node.title or node.url}\n\n")
        w(f"- **URL**: {node.url}\n")
        if node.error:
            w(f"- **Error**: {node.error}\n\n")
            continue
        analysis_page = node.analysis or {}
        if analysis_page.get("page_type"):
            w(f"- **Type**: {analysis_page['page_type']} ({node.analysis_method})\n")
        content = node.content or {}
        w(
            f"- **Words**: {content.get('word_count', 0)} · **Links**: "
            f"{len((node.links or {}).get('internal', []))} internal / "
            f"{len((node.links or {}).get('external', []))} external\n"
        )
        if analysis_page.get("topics"):
            w(
                "- **Topics**: "
                + ", ".join(str(t) for t in analysis_page["topics"][:8])
                + "\n"
            )
        if analysis_page.get("summary"):
            w(f"- **Summary**: {analysis_page['summary']}\n")
        issues = (node.seo or {}).get("issues") or []
        high = [i for i in issues if i["severity"] == "high"]
        if high:
            w(
                "- **Blocking SEO issues**: "
                + "; ".join(i["message"] for i in high[:3])
                + "\n"
            )
        motion = ((node.presentation or {}).get("animation") or {}).get("signals") or []
        if motion:
            w("- **Motion**: " + "; ".join(motion[:3]) + "\n")
        tools = ((node.presentation or {}).get("interactivity") or {}).get(
            "signals"
        ) or []
        if tools and tools != ["no interactive UI detected"]:
            w("- **Interactive**: " + "; ".join(tools[:3]) + "\n")
        downloads = [a for a in (node.assets or []) if a.get("type") == "source"]
        if downloads:
            formats = sorted({d.get("format") for d in downloads if d.get("format")})
            w(f"- **Source downloads**: {len(downloads)} ({', '.join(formats)})\n")
        w("\n")

    if ctx.errors:
        w("## Errors\n\n")
        for err in ctx.errors[:30]:
            w(f"- {err.get('url')} — {err.get('error')}\n")
        w("\n")
    return out.getvalue()


# --------------------------------------------------------------------------- #
# Mermaid link graph
# --------------------------------------------------------------------------- #
def export_mermaid(ctx: SiteContext, max_edges: int = 300) -> str:
    lines = ["graph LR"]
    ids: Dict[str, str] = {}

    def node_id(url: str) -> str:
        if url not in ids:
            ids[url] = f"n{len(ids)}"
        return ids[url]

    for node in ctx.nodes:
        label = (node.title or node.path or node.url)[:48].replace('"', "'")
        shape = (
            f'{node_id(node.url)}["{label}"]'
            if not node.is_index
            else f'{node_id(node.url)}[["{label}"]]'
        )
        lines.append(f"    {shape}")

    known = {n.url for n in ctx.nodes}
    seen: set = set()
    count = 0
    for edge in ctx.edges:
        source, target = edge.get("source"), edge.get("target")
        if source not in known or target not in known or source == target:
            continue
        key = (source, target)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"    {node_id(source)} --> {node_id(target)}")
        count += 1
        if count >= max_edges:
            lines.append(f"    %% truncated at {max_edges} edges")
            break

    seed = ctx.node_by_url(ctx.seed_url)
    if seed is not None:
        lines.append(f"    style {node_id(seed.url)} fill:#2563eb,color:#fff")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
_HTML_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Site context — $title</title>
<style>
:root{--bg:#fff;--card:#f8fafc;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--brand:#2563eb}
@media (prefers-color-scheme:dark){:root{--bg:#0b1120;--card:#111a2e;--ink:#e2e8f0;--muted:#94a3b8;--line:#1e293b;--brand:#60a5fa}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:2rem 1.25rem}
h1{font-size:1.6rem;margin:0 0 .25rem} h2{font-size:1.2rem;margin:2rem 0 .75rem;border-bottom:1px solid var(--line);padding-bottom:.35rem}
h3{font-size:1rem;margin:1.25rem 0 .35rem}
a{color:var(--brand)} .muted{color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.75rem;margin:1rem 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.75rem 1rem}
.stat b{display:block;font-size:1.4rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1rem;margin:.75rem 0}
.badge{display:inline-block;font-size:.75rem;padding:.1rem .5rem;border-radius:999px;border:1px solid var(--line);margin-right:.35rem}
.sw{display:inline-block;width:1.5rem;height:1.5rem;border-radius:4px;border:1px solid var(--line);vertical-align:middle;margin-right:.25rem}
table{border-collapse:collapse;width:100%;font-size:.9rem} th,td{border-bottom:1px solid var(--line);padding:.4rem .5rem;text-align:left}
.scroll{overflow-x:auto}
.high{color:#dc2626} .medium{color:#d97706} .low{color:var(--muted)}
pre{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.75rem;overflow-x:auto;font-size:.8rem}
</style></head><body><div class="wrap">
<h1>$title</h1>
<p class="muted">$subtitle</p>
$body
<p class="muted" style="margin-top:3rem">Generated by $generator · $completed</p>
</div></body></html>
"""
)


def export_html(ctx: SiteContext) -> str:
    e = html_lib.escape
    stats = ctx.stats or {}
    analysis = ctx.site_analysis or {}
    body = io.StringIO()
    w = body.write

    w('<div class="grid">')
    for label, value in (
        ("Pages mapped", stats.get("nodes_total", 0)),
        ("Extracted", stats.get("nodes_extracted", 0)),
        ("Max depth", stats.get("max_depth_reached", 0)),
        ("Edges", len(ctx.edges)),
        ("External refs", len(ctx.external_references)),
        (
            "Interactive pages",
            (ctx.interactivity_profile or {}).get("interactive_pages", 0),
        ),
        ("Analysis", ctx.analysis_method),
    ):
        w(
            f'<div class="stat"><b>{e(str(value))}</b><span class="muted">{e(label)}</span></div>'
        )
    w("</div>")

    if analysis.get("context_brief"):
        w(
            f'<h2>Context brief</h2><div class="card">{e(str(analysis["context_brief"]))}</div>'
        )

    if analysis.get("content_taxonomy"):
        w("<h2>Content clusters</h2>")
        for cluster in analysis["content_taxonomy"]:
            w(f'<div class="card"><h3>{e(str(cluster.get("cluster", "cluster")))}</h3>')
            if cluster.get("theme"):
                w(f'<p class="muted">{e(str(cluster["theme"]))}</p>')
            w("<ul>")
            for url in (cluster.get("pages") or [])[:12]:
                w(
                    f'<li><a href="{e(str(url))}" rel="nofollow noopener">{e(str(url))}</a></li>'
                )
            w("</ul></div>")

    style = ctx.style_profile or {}
    anim = ctx.animation_profile or {}
    if style or anim:
        w("<h2>Presentation</h2><div class='card'>")
        if style.get("palette"):
            w("<p>")
            for entry in style["palette"][:12]:
                color = entry["color"]
                safe = (
                    color
                    if re.fullmatch(r"#[0-9a-fA-F]{3,8}", color)
                    else "transparent"
                )
                w(
                    f'<span class="sw" style="background:{e(safe)}" title="{e(color)}"></span>'
                )
            w("</p>")
        if style.get("font_families"):
            w(f'<p><b>Type:</b> {e(", ".join(style["font_families"][:6]))}</p>')
        for name in (style.get("frameworks") or []) + (
            style.get("js_frameworks") or []
        ):
            w(f'<span class="badge">{e(name)}</span>')
        if anim.get("summary"):
            w(f'<p><b>Motion:</b> {e(str(anim["summary"]))}</p>')
        if anim.get("libraries"):
            w(f'<p><b>Motion libraries:</b> {e(", ".join(anim["libraries"]))}</p>')
        w("</div>")

    inter = ctx.interactivity_profile or {}
    if inter.get("interactive_pages"):
        w(
            f"<h2>Interactive surface</h2><div class='card'><p>{e(inter['summary'])}</p><ul>"
        )
        for page in inter["pages"][:12]:
            label = page.get("title") or page["url"]
            w(
                f'<li><a href="{e(page["url"])}" rel="nofollow noopener">{e(str(label))}</a>'
                f' — {e("; ".join(page["signals"][:2]))}</li>'
            )
        w("</ul></div>")

    seo = ctx.seo_profile or {}
    if seo.get("pages_analyzed"):
        w(
            "<h2>SEO profile</h2><div class='scroll'><table><tr><th>Issue</th><th>Pages</th></tr>"
        )
        for code, count in list((seo.get("issue_counts") or {}).items())[:12]:
            w(f"<tr><td>{e(code)}</td><td>{count}</td></tr>")
        w("</table></div>")

    if ctx.hubs:
        w(
            "<h2>Hubs</h2><div class='scroll'><table><tr><th>Page</th><th>In</th><th>Out</th><th>Depth</th></tr>"
        )
        for hub in ctx.hubs[:12]:
            w(
                f'<tr><td><a href="{e(hub["url"])}" rel="nofollow noopener">'
                f'{e(str(hub.get("title") or hub["url"]))}</a></td>'
                f'<td>{hub.get("in_degree", 0)}</td><td>{hub.get("out_degree", 0)}</td>'
                f'<td>{hub.get("depth", 0)}</td></tr>'
            )
        w("</table></div>")

    w("<h2>Link map</h2><pre>")
    w(e(export_mermaid(ctx, max_edges=200)))
    w("</pre>")

    w("<h2>Pages</h2>")
    for node in sorted(ctx.nodes, key=lambda n: (n.depth, n.url)):
        page = node.analysis or {}
        w('<div class="card">')
        w(
            f'<h3><span class="badge">L{node.depth}</span>'
            f'<a href="{e(node.url)}" rel="nofollow noopener">{e(str(node.title or node.url))}</a></h3>'
        )
        w(f'<p class="muted">{e(node.url)}</p>')
        if node.error:
            w(f'<p class="high">{e(str(node.error))}</p></div>')
            continue
        content = node.content or {}
        w(
            f'<p><span class="badge">{e(str(page.get("page_type") or "page"))}</span>'
            f'<span class="badge">{e(node.analysis_method)}</span>'
            f'<span class="badge">{content.get("word_count", 0)} words</span></p>'
        )
        if page.get("summary"):
            w(f"<p>{e(str(page['summary']))}</p>")
        if page.get("topics"):
            w(
                f'<p class="muted">Topics: {e(", ".join(str(t) for t in page["topics"][:8]))}</p>'
            )
        for issue in ((node.seo or {}).get("issues") or [])[:4]:
            w(f'<div class="{e(issue["severity"])}">• {e(issue["message"])}</div>')
        w("</div>")

    return _HTML_TEMPLATE.substitute(
        title=e(ctx.seed_url),
        subtitle=e(
            f"{stats.get('nodes_total', 0)} pages · depth {(ctx.config or {}).get('depth')} · "
            f"scope {(ctx.config or {}).get('scope')}"
        ),
        body=body.getvalue(),
        generator=e(ctx.generator),
        completed=e(ctx.completed_at or ctx.created_at),
    )


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
def render(ctx: SiteContext, fmt: str) -> str:
    if fmt == "json":
        return export_json(ctx)
    if fmt == "markdown":
        return export_markdown(ctx)
    if fmt == "html":
        return export_html(ctx)
    if fmt == "mermaid":
        return export_mermaid(ctx)
    raise ValueError(f"unknown format {fmt!r}")


def write_export(ctx: SiteContext, fmt: str, out_path) -> Dict[str, Any]:
    from pathlib import Path

    path = Path(out_path)
    text = render(ctx, fmt)
    path.write_text(text, encoding="utf-8")
    return {"format": fmt, "path": str(path), "bytes": len(text.encode("utf-8"))}
