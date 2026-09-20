#!/usr/bin/env python3
"""Search a product repo for PRD elements and lineage witnesses.

Standalone sibling of build_context.py and crawl_site.py: imports the PRD
lineage service directly, so it runs with NO backend and NO API key. Analysis
uses the locally authenticated Claude Code CLI over OAuth; if the CLI is
missing, every source still gets a deterministic heuristic analysis.

Usage:
    python build_prd.py                          # current repo
    python build_prd.py /path/to/product-repo
    python build_prd.py . --map-only
    python build_prd.py . --no-agent --formats json,markdown,mermaid
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.services.prd_lineage import PrdConfig, PrdLineageService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root", nargs="?", default=".", help="Product repo root")
    parser.add_argument("--formats", default="json,markdown")
    parser.add_argument("--output", "-o")
    parser.add_argument("--max-files", type=int, default=400)
    parser.add_argument("--map-only", action="store_true")
    parser.add_argument("--no-agent", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--agent-sources", type=int, default=12)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    cfg = PrdConfig(
        max_files=args.max_files,
        agent_enabled=not args.no_agent,
        agent_model=args.model,
        agent_max_sources=args.agent_sources,
    )
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    out_dir = Path(args.output) if args.output else None
    result = PrdLineageService().run(
        args.repo_root,
        formats=formats,
        cfg=cfg,
        map_only=args.map_only,
        out_dir=out_dir,
    )
    if args.as_json:
        import json

        print(json.dumps(result, indent=2, default=str))
        return 0
    stats = result.get("stats") or {}
    print(f"\n  Repo      : {result.get('repo_root')}")
    print(f"  Product   : {result.get('product_name') or 'unknown'}")
    print(f"  PRD       : {result.get('canonical_prd') or 'missing'}")
    print(
        f"  Map       : {stats.get('sources_total', 0)} sources, "
        f"{stats.get('edges', 0)} citations"
    )
    extract = (result.get("phases") or {}).get("extract") or {}
    if extract:
        print(f"  Extract   : {extract.get('extracted', 0)} files")
    agent = (result.get("phases") or {}).get("agent") or {}
    if args.map_only:
        print("  Agent     : skipped (map-only)")
    else:
        print(
            f"  Agent     : {agent.get('agent_ok', 0)}/{agent.get('agent_calls', 0)} calls, "
            f"{agent.get('heuristic', 0)} heuristic [{result.get('analysis_method')}]"
        )
        print(
            f"  Score     : {result.get('completeness')}/100  "
            f"maturity={result.get('maturity')}"
        )
    if result.get("context_brief"):
        print(f"  Brief     : {result['context_brief']}")
    print(f"  Output    : {result.get('out_dir')}")
    for fmt, info in (result.get("outputs") or {}).items():
        if "error" in info:
            print(f"    - {fmt}: ERROR {info['error']}")
        else:
            print(f"    - {fmt}: {info.get('path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
