"""`aieo crawl` — snapshot a Jekyll/static site into an offline multi-format report.

Runs the snapshot service in-process by default (offline, no server, no API key).
Use --remote to POST to a running REST API instead.
"""

import json
import sys
from pathlib import Path

import click

# Make the backend services importable for the default in-process mode.
_BACKEND = Path(__file__).resolve().parents[3] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@click.command(name="crawl")
@click.argument("base_url")
@click.option(
    "--formats",
    default="json,markdown,html,text",
    help="Comma list: text,json,markdown,html,pdf,bundle",
)
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--max-pages", default=500, show_default=True)
@click.option("--max-depth", default=6, show_default=True)
@click.option(
    "--delay", default=0.25, show_default=True, help="Seconds between live fetches"
)
@click.option("--refresh", is_flag=True, help="Ignore cache validators; re-fetch all")
@click.option("--no-cache", "no_cache", is_flag=True, help="Purge cache and rebuild")
@click.option("--no-robots", "no_robots", is_flag=True, help="Ignore robots.txt")
@click.option("--include-external", is_flag=True, help="Also crawl off-host links")
@click.option("--include-assets", is_flag=True, help="Inline images for offline HTML")
@click.option(
    "--full-page", is_flag=True, help="Keep chrome (skip main-content extraction)"
)
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
def crawl(
    base_url,
    formats,
    output,
    max_pages,
    max_depth,
    delay,
    refresh,
    no_cache,
    no_robots,
    include_external,
    include_assets,
    full_page,
    remote,
    api_url,
    api_key,
    output_json,
):
    """Crawl BASE_URL and write an offline snapshot in the chosen formats."""
    fmt_list = [f.strip() for f in formats.split(",") if f.strip()]

    if remote:
        result = _run_remote(
            base_url,
            fmt_list,
            {
                "max_pages": max_pages,
                "max_depth": max_depth,
                "delay_seconds": delay,
                "refresh": refresh,
                "use_cache": not no_cache,
                "respect_robots": not no_robots,
                "include_external": include_external,
                "include_assets": include_assets,
                "strip_boilerplate": not full_page,
            },
            api_url,
            api_key,
        )
    else:
        result = _run_local(
            base_url,
            fmt_list,
            output,
            max_pages,
            max_depth,
            delay,
            refresh,
            no_cache,
            no_robots,
            include_external,
            include_assets,
            full_page,
        )

    if output_json:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    stats = result.get("stats", {})
    click.echo(f"\nSite:   {result.get('base_url', base_url)}")
    click.echo(
        f"Pages:  {stats.get('pages_total', 0)} "
        f"({stats.get('pages_from_cache', 0)} cached, "
        f"{stats.get('pages_changed', 0)} changed, {stats.get('pages_new', 0)} new)"
    )
    click.echo(f"Output: {result.get('out_dir', '(remote)')}")
    for fmt, info in result.get("outputs", {}).items():
        if "error" in info:
            click.echo(f"  - {fmt}: ERROR {info['error']}")
        else:
            engine = f" [{info['engine']}]" if info.get("engine") else ""
            click.echo(
                f"  - {fmt}: {info.get('bytes', 0):,} bytes{engine} {info.get('path', '')}"
            )


def _run_local(
    base_url,
    formats,
    output,
    max_pages,
    max_depth,
    delay,
    refresh,
    no_cache,
    no_robots,
    include_external,
    include_assets,
    full_page,
):
    from app.services.site_snapshot import CrawlConfig, SiteSnapshotService

    cfg = CrawlConfig(
        max_pages=max_pages,
        max_depth=max_depth,
        delay_seconds=delay,
        refresh=refresh,
        use_cache=not no_cache,
        respect_robots=not no_robots,
        include_external=include_external,
        include_assets=include_assets,
        strip_boilerplate=not full_page,
    )
    svc = SiteSnapshotService()
    out_dir = Path(output) if output else None
    try:
        return svc.snapshot(base_url, formats=formats, cfg=cfg, out_dir=out_dir)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


def _run_remote(base_url, formats, knobs, api_url, api_key):
    import httpx

    headers = {"X-API-Key": api_key} if api_key else {}
    payload = {"base_url": base_url, "formats": formats, **knobs}
    try:
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(
                f"{api_url}/aieo/snapshot", json=payload, headers=headers
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
