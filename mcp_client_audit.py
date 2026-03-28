#!/usr/bin/env python3
"""MCP client that connects to the AIEO MCP server and audits sites.

Spawns the MCP server as a subprocess, communicates over JSON-RPC/stdio,
and calls the aieo_audit_url and aieo_list_patterns tools for each site.

Usage:
    python mcp_client_audit.py                              # defaults
    python mcp_client_audit.py --sites sites.txt --output reports
    docker compose run --rm mcp-audit                       # via Docker
"""

import argparse
import asyncio
import base64
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def call_tool(session: ClientSession, name: str, arguments: dict) -> dict:
    """Call an MCP tool and return the parsed JSON result."""
    result = await session.call_tool(name, arguments)
    for content in result.content:
        if hasattr(content, "text"):
            return json.loads(content.text)
    return {"error": "No text content in response"}


def site_label(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.strip("/")
    return f"{host}/{path}" if path else host


def url_to_filename(url: str) -> str:
    parsed = urlparse(url)
    name = parsed.netloc.replace("www.", "").replace(".", "_")
    path = parsed.path.strip("/").replace("/", "_")
    return f"{name}_{path}" if path else name


def format_score(score) -> str:
    val = round(float(score), 1)
    return str(int(val)) if val == int(val) else str(val)


async def run_audit(sites_file: str, output_dir: str, server_cmd: list[str]):
    """Connect to MCP server and audit all sites."""
    sites_path = Path(sites_file)
    urls = [
        line.strip()
        for line in sites_path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    server_params = StdioServerParameters(
        command=server_cmd[0],
        args=server_cmd[1:],
        env=dict(os.environ),
    )

    print(f"Starting MCP server: {' '.join(server_cmd)}")
    print(f"Auditing {len(urls)} sites → {out}/\n")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Step 1: List patterns via MCP tool
            print("=" * 80)
            print("STEP 1: Listing AIEO patterns via aieo_list_patterns tool")
            print("=" * 80)
            patterns = await call_tool(session, "aieo_list_patterns", {})
            print(f"\n{'Pattern':<30} {'Weight':>7} {'Max':>5}")
            print("-" * 45)
            for p in patterns:
                print(f"  {p['display_name']:<28} {p['weight']:>7} {p['max_score']:>5}")
            total_weight = sum(p["weight"] for p in patterns)
            print(f"  {'TOTAL':<28} {total_weight:>7}")
            print()

            # Step 2: Audit each URL via aieo_audit_url tool
            print("=" * 80)
            print("STEP 2: Auditing sites via aieo_audit_url tool")
            print("=" * 80)

            summary = []
            for i, url in enumerate(urls, 1):
                print(f"\n[{i}/{len(urls)}] aieo_audit_url({url})")
                result = await call_tool(session, "aieo_audit_url", {"url": url})

                if "error" in result:
                    print(f"  ✗ ERROR: {result['error']}")
                    summary.append({
                        "url": url, "status": "error", "error": result["error"],
                        "score": None, "grade": None, "word_count": None,
                        "gap_count": None, "method": None,
                    })
                    # Save error result
                    fname = url_to_filename(url)
                    (out / f"{fname}.json").write_text(json.dumps(
                        {"url": url, "status": "error", "error": result["error"],
                         "timestamp": datetime.now().isoformat()}, indent=2))
                    continue

                score = result.get("score", 0)
                grade = result.get("grade", "?")
                method = result.get("scoring_method", "?")
                words = result.get("word_count", 0)
                gaps = result.get("gaps", [])
                assessment = result.get("overall_assessment", "")

                print(f"  ✓ Score: {format_score(score)}/100  Grade: {grade}  [{method}]")
                print(f"    Words: {words}  Gaps: {len(gaps)}")
                if assessment:
                    print(f"    Assessment: {assessment[:100]}")

                # Show top pattern scores
                ps = result.get("pattern_scores", {})
                top = sorted(ps.items(), key=lambda kv: kv[1].get("score", 0), reverse=True)[:3]
                if top:
                    top_str = ", ".join(
                        f"{n.replace('_',' ').title()}: {format_score(v['score'])}/{format_score(v['max'])}"
                        for n, v in top
                    )
                    print(f"    Top patterns: {top_str}")

                # Save individual result
                result["timestamp"] = datetime.now().isoformat()
                result["status"] = "success"
                fname = url_to_filename(url)

                # Save screenshot as PNG if present
                screenshot_b64 = result.pop("screenshot_b64", None)
                if screenshot_b64:
                    png_path = out / f"{fname}.png"
                    png_path.write_bytes(base64.b64decode(screenshot_b64))
                    result["screenshot_file"] = f"{fname}.png"
                    print(f"    📸 Screenshot saved: {fname}.png")

                (out / f"{fname}.json").write_text(
                    json.dumps(result, indent=2, default=str))

                summary.append({
                    "url": url, "status": "success",
                    "score": score, "grade": grade,
                    "word_count": words, "gap_count": len(gaps),
                    "method": method, "error": None,
                })

            # Save summary
            (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))

            # Step 3: Print summary table
            print("\n" + "=" * 80)
            print("STEP 3: Audit Summary")
            print("=" * 80)
            print(f"\n{'URL':<40} {'Score':>6} {'Grade':>6} {'Words':>7} {'Gaps':>5} {'Method':>10}")
            print("-" * 80)
            for s in summary:
                if s["status"] == "success":
                    print(f"{site_label(s['url'])[:39]:<40} "
                          f"{format_score(s['score']):>6} {s['grade']:>6} "
                          f"{s['word_count']:>7} {s['gap_count']:>5} "
                          f"{s['method']:>10}")
                else:
                    print(f"{site_label(s['url'])[:39]:<40} "
                          f"{'ERR':>6} {'--':>6} {'--':>7} {'--':>5} "
                          f"{'--':>10}  ({s.get('error', '?')[:30]})")

            scores = [s["score"] for s in summary if s["status"] == "success"]
            if scores:
                avg = sum(scores) / len(scores)
                print("-" * 80)
                print(f"{'Average':<40} {format_score(avg):>6}")

            print(f"\nResults saved to: {out}/")


def main():
    parser = argparse.ArgumentParser(description="MCP client that audits sites via AIEO MCP tools")
    parser.add_argument("--sites", default="sites.txt", help="Path to URL list")
    parser.add_argument("--output", default="reports", help="Output directory")
    parser.add_argument("--server-cmd", default=None,
                        help="MCP server command (default: python -m app.mcp_server)")
    args = parser.parse_args()

    # Determine server command
    if args.server_cmd:
        server_cmd = args.server_cmd.split()
    else:
        # Auto-detect: if running inside backend/ dir or in container
        if Path("app/mcp_server.py").exists():
            server_cmd = [sys.executable, "-m", "app.mcp_server"]
        elif Path("backend/app/mcp_server.py").exists():
            server_cmd = [sys.executable, "-m", "backend.app.mcp_server"]
        else:
            server_cmd = [sys.executable, "-m", "app.mcp_server"]

    asyncio.run(run_audit(args.sites, args.output, server_cmd))


if __name__ == "__main__":
    main()
