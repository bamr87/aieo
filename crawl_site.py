#!/usr/bin/env python3
"""Crawl a Jekyll/static site into a cached, offline, multi-format snapshot.

A standalone sibling of run_audit.py: imports the snapshot service directly, so
it runs with NO backend, NO API key, and only the lean dependency set
(httpx + beautifulsoup4 + markdown + html2text). Everything else is stdlib.

Usage:
    python crawl_site.py https://bashconsultants.com
    python crawl_site.py https://bashconsultants.com --formats text,json,markdown,html,pdf,bundle
    python crawl_site.py https://bashconsultants.com --output ./snapshot --max-pages 300
    python crawl_site.py --sites sites.txt --formats html,json     # batch
    python crawl_site.py https://example.com --refresh             # ignore cache validators
    python crawl_site.py https://example.com --no-cache            # rebuild from scratch

Re-running is cheap: unchanged pages come back via HTTP 304 / content-hash match
and are served from the on-disk cache under <workspace>/.cache/snapshots/<site>/.
"""

import argparse
import os
import sys
from pathlib import Path

# Import the service directly from the backend, like run_audit.py.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.services.site_snapshot import CrawlConfig, SiteSnapshotService  # noqa: E402


def build_config(args) -> CrawlConfig:
    return CrawlConfig(
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        max_link_pages=args.max_link_pages,
        delay_seconds=args.delay,
        respect_robots=not args.no_robots,
        use_cache=not args.no_cache,
        refresh=args.refresh,
        ttl_seconds=args.ttl,
        include_external=args.include_external,
        include_assets=args.include_assets,
        strip_boilerplate=not args.full_page,
    )


def print_summary(result: dict) -> None:
    stats = result.get("stats", {})
    disc = result.get("discovery", {})
    print(f"\n  Site      : {result['base_url']}")
    print(
        f"  Discovery : {disc.get('source')} "
        f"(sitemap={disc.get('sitemap_urls', 0)}, feed={disc.get('feed_urls', 0)}, "
        f"links={disc.get('link_followed', 0)})"
    )
    print(
        f"  Pages     : {stats.get('pages_total', 0)} "
        f"({stats.get('pages_ok', 0)} ok, {stats.get('pages_from_cache', 0)} cached, "
        f"{stats.get('pages_changed', 0)} changed, {stats.get('pages_new', 0)} new, "
        f"{stats.get('pages_error', 0)} error)"
    )
    print(
        f"  Cache hit : {stats.get('cache_hit_rate', 0) * 100:.0f}%   "
        f"Time: {stats.get('crawl_seconds', 0)}s"
        f"{'   [DEGRADED]' if result.get('degraded') else ''}"
    )
    print(f"  Output    : {result.get('out_dir')}")
    for fmt, info in result.get("outputs", {}).items():
        if "error" in info:
            print(f"    - {fmt:<9} ERROR: {info['error']}")
        else:
            engine = f" [{info['engine']}]" if info.get("engine") else ""
            print(
                f"    - {fmt:<9} {info['bytes']:>9,} bytes{engine}  {Path(info['path']).name}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AIEO Site Snapshot — offline site crawler"
    )
    parser.add_argument(
        "base_url", nargs="?", help="Site URL, e.g. https://bashconsultants.com"
    )
    parser.add_argument("--sites", help="File with one URL per line (batch mode)")
    parser.add_argument(
        "--formats",
        default="json,markdown,html,text",
        help="Comma list: text,json,markdown,html,pdf,bundle",
    )
    parser.add_argument(
        "--output", "-o", help="Output directory (default: workspace audits dir)"
    )
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument(
        "--max-link-pages",
        type=int,
        default=200,
        help="Budget for pages discovered by link-following (not in sitemap)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.25, help="Seconds between live fetches"
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=0,
        help="Skip revalidation for entries younger than N seconds",
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Ignore cache validators; re-fetch all"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Purge the site cache and rebuild"
    )
    parser.add_argument(
        "--no-robots", action="store_true", help="Ignore robots.txt rules"
    )
    parser.add_argument(
        "--include-external", action="store_true", help="Also crawl off-host links"
    )
    parser.add_argument(
        "--include-assets",
        action="store_true",
        help="Download + inline images as data URIs (offline HTML/bundle)",
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Keep nav/header/footer/chrome instead of extracting main content only",
    )
    args = parser.parse_args()

    if args.sites:
        sites = [
            line.strip()
            for line in Path(args.sites).read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    elif args.base_url:
        sites = [args.base_url]
    else:
        parser.error("Provide a base_url or --sites file")

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    cfg = build_config(args)
    svc = SiteSnapshotService()

    print(f"Snapshotting {len(sites)} site(s); formats={formats}")
    for i, url in enumerate(sites, 1):
        print(f"\n[{i}/{len(sites)}] {url}")
        try:
            out_dir = Path(args.output) if args.output else None
            result = svc.snapshot(url, formats=formats, cfg=cfg, out_dir=out_dir)
            print_summary(result)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}")


if __name__ == "__main__":
    main()
