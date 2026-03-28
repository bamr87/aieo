#!/usr/bin/env python3
"""Run AIEO audit on all sites listed in sites.txt and output results to a temp directory.

Supports AI-driven scoring when OPENAI_API_KEY or ANTHROPIC_API_KEY is set.
Falls back to heuristic scoring otherwise.

Usage:
    python run_audit.py                         # heuristic mode
    OPENAI_API_KEY=sk-... python run_audit.py   # AI-driven mode
    python run_audit.py --provider openai --model gpt-4o
"""

import argparse
import sys
import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

# Add backend to path so we can import the scoring engine directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.services.scoring_engine import ScoringEngine


def fetch_url(url: str) -> str:
    """Fetch HTML content from a URL."""
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(
            url,
            headers={"User-Agent": "AIEO-Bot/1.0 (Content Analysis Tool)"},
        )
        response.raise_for_status()
        return response.text


def url_to_filename(url: str) -> str:
    """Convert a URL into a safe filename."""
    parsed = urlparse(url)
    name = parsed.netloc.replace("www.", "").replace(".", "_")
    path = parsed.path.strip("/").replace("/", "_")
    if path:
        name = f"{name}_{path}"
    return name


def main():
    parser = argparse.ArgumentParser(description="AIEO Batch Audit")
    parser.add_argument("--provider", choices=["openai", "anthropic"], help="AI provider")
    parser.add_argument("--model", help="Model name (e.g., gpt-4o, claude-sonnet-4-20250514)")
    parser.add_argument("--api-key", help="API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var)")
    parser.add_argument("--sites", default="sites.txt", help="Path to sites file")
    parser.add_argument("--output", help="Output directory (default: auto-generated temp dir)")
    args = parser.parse_args()

    sites_file = Path(args.sites)
    if not sites_file.exists():
        sites_file = Path(__file__).parent / args.sites
    urls = [
        line.strip()
        for line in sites_file.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    # Create output directory
    output_dir = Path(args.output) if args.output else Path(tempfile.mkdtemp(prefix="aieo_results_"))
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    engine = ScoringEngine(
        provider=args.provider,
        api_key=args.api_key,
        model=args.model,
    )

    mode = engine.provider or "heuristic"
    model_name = engine.model or "n/a"
    print(f"Scoring mode: {mode}  Model: {model_name}")

    summary = []

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Auditing: {url}")
        result = {"url": url, "timestamp": datetime.now().isoformat()}

        try:
            html_content = fetch_url(url)
            score_result = engine.score(html_content, format="html")

            result["status"] = "success"
            result.update({
                "score": score_result["score"],
                "grade": score_result["grade"],
                "word_count": score_result["word_count"],
                "scoring_method": score_result.get("scoring_method", "unknown"),
                "content_type": score_result.get("content_type", "unknown"),
                "overall_assessment": score_result.get("overall_assessment", ""),
                "pattern_scores": score_result["pattern_scores"],
                "gaps": score_result["gaps"],
                "anti_pattern_penalties": score_result["anti_pattern_penalties"],
            })

            print(f"  Score: {score_result['score']}/100  Grade: {score_result['grade']}  [{score_result.get('scoring_method', '?')}]")
            print(f"  Word count: {score_result['word_count']}")
            if score_result.get("overall_assessment"):
                print(f"  Assessment: {score_result['overall_assessment'][:120]}")
            if score_result["gaps"]:
                print(f"  Gaps ({len(score_result['gaps'])}):")
                for gap in score_result["gaps"][:3]:
                    print(f"    - [{gap['severity']}] {gap['description'][:80]}")

        except httpx.HTTPStatusError as e:
            result["status"] = "error"
            result["error"] = f"HTTP {e.response.status_code}"
            print(f"  ERROR: HTTP {e.response.status_code}")
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"  ERROR: {e}")

        # Save individual result
        filename = url_to_filename(url)
        result_path = output_dir / f"{filename}.json"
        result_path.write_text(json.dumps(result, indent=2, default=str))

        summary.append({
            "url": url,
            "status": result.get("status"),
            "score": result.get("score"),
            "grade": result.get("grade"),
            "word_count": result.get("word_count"),
            "gap_count": len(result.get("gaps", [])),
            "method": result.get("scoring_method"),
            "error": result.get("error"),
        })

    # Save summary
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))

    # Print summary table
    print("\n" + "=" * 90)
    print("AIEO AUDIT SUMMARY")
    print("=" * 90)
    print(f"{'URL':<40} {'Score':>6} {'Grade':>6} {'Words':>7} {'Gaps':>5} {'Method':>10}")
    print("-" * 90)
    for s in summary:
        if s["status"] == "success":
            print(f"{s['url'][:39]:<40} {s['score']:>6} {s['grade']:>6} {s['word_count']:>7} {s['gap_count']:>5} {s.get('method', '?'):>10}")
        else:
            print(f"{s['url'][:39]:<40} {'ERR':>6} {'--':>6} {'--':>7} {'--':>5} {'--':>10}  ({s.get('error', 'unknown')})")
    print("=" * 90)
    print(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()
