#!/usr/bin/env python3
"""Crawl a URL N levels down into a contextual dataset of the site.

A standalone sibling of crawl_site.py and run_audit.py: imports the context
service directly, so it runs with NO backend and NO API key. The analysis pass
uses the locally authenticated **Claude Code CLI over OAuth** (`claude`); if the
CLI is not installed or not logged in, every page still gets a deterministic
heuristic analysis and the run reports `analysis_method: heuristic`.

Three phases: map the links and references -> extract content, metadata,
styles/images/animation and SEO facts -> loop the pages through the agent.

Usage:
    python build_context.py https://www.nayuki.io/category/programming
    python build_context.py https://example.com/docs --depth 3 --scope path
    python build_context.py https://example.com/blog --map-only        # phase 1 only
    python build_context.py https://example.com --no-agent             # phases 1-2 only
    python build_context.py https://example.com --formats json,markdown,html,mermaid
    python build_context.py --seeds seeds.txt --depth 1                # batch

Re-running is cheap: bodies are cached (shared with `crawl_site.py`) and revalidated
with ETag / Last-Modified, so unchanged pages are not re-downloaded.
"""

import argparse
import os
import sys
from pathlib import Path

# Import the service directly from the backend, like crawl_site.py.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.services.site_context import ContextConfig, SiteContextService  # noqa: E402


def build_config(args) -> ContextConfig:
    return ContextConfig(
        depth=args.depth,
        scope=args.scope,
        max_pages=args.max_pages,
        max_pages_per_level=args.max_per_level,
        follow_sitemap=args.follow_sitemap,
        include_external=args.include_external,
        delay_seconds=args.delay,
        respect_robots=not args.no_robots,
        use_cache=not args.no_cache,
        refresh=args.refresh,
        ttl_seconds=args.ttl,
        strip_boilerplate=not args.full_page,
        capture_presentation=not args.no_presentation,
        fetch_stylesheets=not args.no_css,
        fetch_scripts=not args.no_js,
        keep_interactive=not args.no_interactive,
        extractor=args.extractor,
        use_optional_libraries=not args.no_libraries,
        render=args.render,
        render_wait_ms=args.render_wait,
        agent_enabled=not args.no_agent,
        agent_model=args.model,
        agent_max_pages=args.agent_pages,
        agent_concurrency=args.agent_concurrency,
        agent_timeout=args.agent_timeout,
        agent_synthesis=not args.no_synthesis,
    )


def print_summary(result: dict) -> None:
    stats = result.get("stats", {})
    phases = result.get("phases", {})
    agent = phases.get("agent", {})
    hist = result.get("depth_histogram", {})

    print(f"\n  Seed      : {result['seed_url']}")
    print(
        f"  Map       : {stats.get('nodes_total', 0)} pages "
        f"({', '.join(f'L{d}={n}' for d, n in hist.items()) or 'none'}), "
        f"{stats.get('edges', 0)} links, {stats.get('external_refs', 0)} external refs"
    )
    extract = phases.get("extract", {})
    if "skipped" in extract:
        print(f"  Extract   : skipped ({extract['skipped']})")
    else:
        print(
            f"  Extract   : {extract.get('extracted', 0)} pages, "
            f"{extract.get('stylesheets_fetched', 0)} stylesheets, "
            f"{extract.get('scripts_fetched', 0)} scripts, "
            f"{extract.get('failed', 0)} failed"
        )
    render = (phases.get("map") or {}).get("render_fallback")
    if render:
        print(f"  Render    : unavailable — {render}")
    if "skipped" in agent:
        print(f"  Agent     : skipped ({agent['skipped']})")
    else:
        print(
            f"  Agent     : {agent.get('agent_ok', 0)}/{agent.get('agent_calls', 0)} "
            f"Claude Code calls ok, {agent.get('heuristic', 0)} heuristic "
            f"[{result.get('analysis_method')}]"
        )
        if agent.get("skipped_reason"):
            print(f"              {agent['skipped_reason']}")
    print(
        f"  Time      : {stats.get('total_seconds', 0)}s"
        f"{'   [DEGRADED]' if result.get('degraded') else ''}"
    )
    if result.get("context_brief"):
        print(f"  Brief     : {result['context_brief'][:300]}")
    print(f"  Output    : {result.get('out_dir')}")
    for fmt, info in result.get("outputs", {}).items():
        if "error" in info:
            print(f"    - {fmt:<9} ERROR: {info['error']}")
        else:
            print(
                f"    - {fmt:<9} {info['bytes']:>9,} bytes  {Path(info['path']).name}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AIEO Site Context — crawl a URL N levels down into a dataset"
    )
    parser.add_argument(
        "seed_url",
        nargs="?",
        help="Start URL, e.g. https://www.nayuki.io/category/programming",
    )
    parser.add_argument("--seeds", help="File with one URL per line (batch mode)")
    parser.add_argument(
        "--formats",
        default="json,markdown",
        help="Comma list: json,markdown,html,mermaid",
    )
    parser.add_argument("--output", "-o", help="Output directory (default: workspace)")

    # Phase 1 — mapping
    parser.add_argument(
        "--depth", "-d", type=int, default=2, help="Levels below the seed"
    )
    parser.add_argument(
        "--scope",
        default="host",
        choices=["host", "domain", "path"],
        help="host: same site; domain: include subdomains; path: only under the seed path",
    )
    parser.add_argument("--max-pages", type=int, default=150)
    parser.add_argument("--max-per-level", type=int, default=80)
    parser.add_argument(
        "--follow-sitemap",
        action="store_true",
        help="Also seed level 1 from sitemap.xml URLs that are in scope",
    )
    parser.add_argument(
        "--include-external", action="store_true", help="Crawl off-scope links too"
    )
    parser.add_argument(
        "--delay", type=float, default=0.25, help="Seconds between live fetches"
    )
    parser.add_argument(
        "--ttl", type=int, default=0, help="Skip revalidation under N seconds old"
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Ignore cache validators"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Purge the cache and rebuild"
    )
    parser.add_argument(
        "--no-robots", action="store_true", help="Ignore robots.txt rules"
    )

    # Phase 2 — extraction
    parser.add_argument(
        "--full-page", action="store_true", help="Keep nav/footer chrome"
    )
    parser.add_argument(
        "--no-presentation",
        action="store_true",
        help="Skip the style/image/animation profile",
    )
    parser.add_argument(
        "--no-css", action="store_true", help="Do not fetch linked stylesheets"
    )
    parser.add_argument(
        "--no-js",
        action="store_true",
        help="Do not fetch same-host scripts (skips script-driven motion detection)",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Drop in-page tools (forms, hidden demos) as chrome",
    )
    parser.add_argument(
        "--extractor",
        default="auto",
        choices=["auto", "builtin", "trafilatura"],
        help="Main-content engine (auto: library for articles, built-in for hubs)",
    )
    parser.add_argument(
        "--no-libraries",
        action="store_true",
        help="Ignore optional libraries (trafilatura/extruct/protego) even if installed",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Execute JavaScript via Playwright and crawl the rendered DOM (slow)",
    )
    parser.add_argument(
        "--render-wait",
        type=int,
        default=600,
        help="ms to settle after load (with --render)",
    )

    # Phase 3 — Claude Code agent (OAuth)
    parser.add_argument(
        "--no-agent", action="store_true", help="Skip the agent pass entirely"
    )
    parser.add_argument("--model", help="Claude Code model alias (default: sonnet)")
    parser.add_argument(
        "--agent-pages", type=int, default=25, help="Max pages sent to the agent"
    )
    parser.add_argument("--agent-concurrency", type=int, default=3)
    parser.add_argument("--agent-timeout", type=int, default=180)
    parser.add_argument(
        "--no-synthesis", action="store_true", help="Skip the site-level pass"
    )

    parser.add_argument(
        "--map-only",
        action="store_true",
        help="Phase 1 only: just the link/reference map",
    )
    args = parser.parse_args()

    if args.seeds:
        seeds = [
            line.strip()
            for line in Path(args.seeds).read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    elif args.seed_url:
        seeds = [args.seed_url]
    else:
        parser.error("Provide a seed_url or --seeds file")

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    cfg = build_config(args)
    svc = SiteContextService()

    print(
        f"Building context for {len(seeds)} seed(s); depth={cfg.depth} "
        f"scope={cfg.scope} formats={formats}"
        f"{' [map-only]' if args.map_only else ''}"
    )
    failures = 0
    for i, url in enumerate(seeds, 1):
        print(f"\n[{i}/{len(seeds)}] {url}")
        try:
            out_dir = Path(args.output) if args.output else None
            result = svc.run(
                url,
                formats=formats,
                cfg=cfg,
                out_dir=out_dir,
                map_only=args.map_only,
            )
            print_summary(result)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  ERROR: {exc}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
