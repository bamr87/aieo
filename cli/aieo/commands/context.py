"""`aieo context` — crawl a URL N levels down into a contextual dataset.

Runs the context service in-process by default (offline, no server, no API key;
the analysis pass uses the local Claude Code CLI over OAuth). Use --remote to
POST to a running REST API instead.
"""

import json
import sys
from pathlib import Path

import click

# Make the backend services importable for the default in-process mode.
_BACKEND = Path(__file__).resolve().parents[3] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@click.command(name="context")
@click.argument("seed_url")
@click.option(
    "--depth", "-d", default=2, show_default=True, help="Levels below the seed"
)
@click.option(
    "--scope",
    default="host",
    show_default=True,
    type=click.Choice(["host", "domain", "path"]),
    help="host: same site · domain: with subdomains · path: only under the seed path",
)
@click.option(
    "--formats", default="json,markdown", help="Comma list: json,markdown,html,mermaid"
)
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--max-pages", default=150, show_default=True)
@click.option("--max-per-level", default=80, show_default=True)
@click.option(
    "--follow-sitemap", is_flag=True, help="Seed level 1 from sitemap.xml too"
)
@click.option(
    "--delay", default=0.25, show_default=True, help="Seconds between live fetches"
)
@click.option("--refresh", is_flag=True, help="Ignore cache validators; re-fetch all")
@click.option("--no-cache", "no_cache", is_flag=True, help="Purge cache and rebuild")
@click.option("--no-robots", "no_robots", is_flag=True, help="Ignore robots.txt")
@click.option("--include-external", is_flag=True, help="Also crawl off-scope links")
@click.option(
    "--full-page", is_flag=True, help="Keep chrome (skip main-content extraction)"
)
@click.option(
    "--no-css", "no_css", is_flag=True, help="Do not fetch linked stylesheets"
)
@click.option("--no-js", "no_js", is_flag=True, help="Do not fetch same-host scripts")
@click.option(
    "--no-interactive",
    "no_interactive",
    is_flag=True,
    help="Drop in-page tools (forms, hidden demos) as chrome",
)
@click.option(
    "--extractor",
    default="auto",
    show_default=True,
    type=click.Choice(["auto", "builtin", "trafilatura"]),
    help="Main-content engine (auto: library for articles, built-in for hubs)",
)
@click.option(
    "--no-libraries",
    "no_libraries",
    is_flag=True,
    help="Ignore optional libraries (trafilatura/extruct/protego) even if installed",
)
@click.option(
    "--render", is_flag=True, help="Render JavaScript via Playwright (slow, opt-in)"
)
@click.option("--map-only", is_flag=True, help="Phase 1 only: the link/reference map")
@click.option(
    "--no-agent", "no_agent", is_flag=True, help="Skip the Claude Code agent pass"
)
@click.option("--model", help="Claude Code model alias (default: sonnet)")
@click.option(
    "--agent-pages", default=25, show_default=True, help="Max pages sent to the agent"
)
@click.option("--agent-concurrency", default=3, show_default=True)
@click.option(
    "--remote", is_flag=True, help="POST to the REST API instead of running in-process"
)
@click.option(
    "--api-url",
    default="http://localhost:8000/api/v1",
    help="API base URL (with --remote)",
)
@click.option("--api-key", envvar="AIEO_API_KEY", help="API key (or set AIEO_API_KEY)")
@click.option("--json", "output_json", is_flag=True, help="Print the raw result JSON")
def context(
    seed_url,
    depth,
    scope,
    formats,
    output,
    max_pages,
    max_per_level,
    follow_sitemap,
    delay,
    refresh,
    no_cache,
    no_robots,
    include_external,
    full_page,
    no_css,
    no_js,
    no_interactive,
    extractor,
    no_libraries,
    render,
    map_only,
    no_agent,
    model,
    agent_pages,
    agent_concurrency,
    remote,
    api_url,
    api_key,
    output_json,
):
    """Crawl SEED_URL and the pages N levels below it into a contextual dataset.

    Three phases: map the links and references, extract content/metadata/styles/
    images/animation/SEO, then loop the pages through a Claude Code agent (OAuth).
    """
    fmt_list = [f.strip() for f in formats.split(",") if f.strip()]
    knobs = {
        "depth": depth,
        "scope": scope,
        "max_pages": max_pages,
        "max_pages_per_level": max_per_level,
        "follow_sitemap": follow_sitemap,
        "delay_seconds": delay,
        "refresh": refresh,
        "use_cache": not no_cache,
        "respect_robots": not no_robots,
        "include_external": include_external,
        "strip_boilerplate": not full_page,
        "fetch_stylesheets": not no_css,
        "fetch_scripts": not no_js,
        "keep_interactive": not no_interactive,
        "extractor": extractor,
        "use_optional_libraries": not no_libraries,
        "render": render,
        "agent_enabled": not no_agent,
        "agent_model": model,
        "agent_max_pages": agent_pages,
        "agent_concurrency": agent_concurrency,
    }

    if remote:
        result = _run_remote(seed_url, fmt_list, knobs, map_only, api_url, api_key)
    else:
        result = _run_local(seed_url, fmt_list, knobs, map_only, output)

    if output_json:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    stats = result.get("stats", {})
    phases = result.get("phases", {})
    agent = phases.get("agent", {})
    hist = result.get("depth_histogram", {})
    click.echo(f"\nSeed:     {result.get('seed_url', seed_url)}")
    click.echo(
        f"Map:      {stats.get('nodes_total', 0)} pages "
        f"({', '.join(f'L{d}={n}' for d, n in hist.items()) or 'none'}), "
        f"{stats.get('edges', 0)} links"
    )
    extract = phases.get("extract", {})
    if "skipped" in extract:
        click.echo(f"Extract:  skipped ({extract['skipped']})")
    else:
        click.echo(
            f"Extract:  {extract.get('extracted', 0)} pages, "
            f"{extract.get('stylesheets_fetched', 0)} stylesheets"
        )
    if "skipped" in agent:
        click.echo(f"Agent:    skipped ({agent['skipped']})")
    else:
        click.echo(
            f"Agent:    {agent.get('agent_ok', 0)}/{agent.get('agent_calls', 0)} calls, "
            f"{agent.get('heuristic', 0)} heuristic [{result.get('analysis_method')}]"
        )
    if result.get("context_brief"):
        click.echo(f"Brief:    {result['context_brief'][:280]}")
    click.echo(f"Output:   {result.get('out_dir', '(remote)')}")
    for fmt, info in (result.get("outputs") or {}).items():
        if "error" in info:
            click.echo(f"  - {fmt}: ERROR {info['error']}")
        else:
            click.echo(
                f"  - {fmt}: {info.get('bytes', 0):,} bytes {info.get('path', '')}"
            )


def _run_local(seed_url, formats, knobs, map_only, output):
    from app.services.site_context import ContextConfig, SiteContextService

    cfg = ContextConfig.from_dict(knobs)
    svc = SiteContextService()
    out_dir = Path(output) if output else None
    try:
        return svc.run(
            seed_url, formats=formats, cfg=cfg, out_dir=out_dir, map_only=map_only
        )
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


def _run_remote(seed_url, formats, knobs, map_only, api_url, api_key):
    import httpx

    headers = {"X-API-Key": api_key} if api_key else {}
    payload = {
        "seed_url": seed_url,
        "formats": formats,
        "map_only": map_only,
        **{k: v for k, v in knobs.items() if v is not None},
    }
    try:
        with httpx.Client(timeout=900.0) as client:
            resp = client.post(f"{api_url}/aieo/context", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
