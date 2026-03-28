#!/usr/bin/env python3
"""Generate human-readable markdown reports from AIEO JSON audit results.

Reads individual site JSON files and summary.json from a reports directory,
then produces:
  - One per-site markdown report (site_name.md)
  - One combined summary report (REPORT.md)

Usage:
    python generate_reports.py                        # defaults: reports/ -> reports/
    python generate_reports.py --input reports --output reports
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_site_reports(input_dir: Path) -> list[dict]:
    """Load all individual site JSON files (excludes summary.json)."""
    reports = []
    for f in sorted(input_dir.glob("*.json")):
        if f.name == "summary.json":
            continue
        data = json.loads(f.read_text())
        data["_source_file"] = f.name
        reports.append(data)
    return reports


def score_bar(score: float, max_score: float, width: int = 20) -> str:
    """Render a text progress bar: [████████░░░░░░░░░░░░]"""
    ratio = score / max_score if max_score else 0
    filled = round(ratio * width)
    return f"`{'█' * filled}{'░' * (width - filled)}`"


def grade_emoji(grade: str) -> str:
    return {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}.get(grade, "⚪")


def severity_icon(severity: str) -> str:
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")


def site_label(url: str) -> str:
    """Return a clean display name from a URL."""
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.strip("/")
    return f"{host}/{path}" if path else host


def format_score(score) -> str:
    """Round to one decimal, drop trailing .0"""
    val = round(float(score), 1)
    return str(int(val)) if val == int(val) else str(val)


# ---------------------------------------------------------------------------
# Per-site report
# ---------------------------------------------------------------------------

def render_site_report(data: dict) -> str:
    """Render a full markdown report for one site."""
    url = data.get("url", "unknown")
    label = site_label(url)
    score = float(data.get("score", 0))
    grade = data.get("grade", "?")
    word_count = data.get("word_count", 0)
    method = data.get("scoring_method", "unknown")
    content_type = data.get("content_type", "unknown")
    assessment = data.get("overall_assessment", "")
    executive_summary = data.get("executive_summary", "")
    priority_actions = data.get("priority_actions", [])
    sample_improvements = data.get("sample_improvements", [])
    visual_analysis = data.get("visual_analysis", {})
    screenshot_file = data.get("screenshot_file", "")
    timestamp = data.get("timestamp", "")
    patterns = data.get("pattern_scores", {})
    gaps = data.get("gaps", [])
    anti_penalties = data.get("anti_pattern_penalties", 0)
    model = data.get("model", "")
    provider = data.get("provider", "")

    lines = []
    w = lines.append

    w(f"# AIEO Audit Report: {label}")
    w("")

    # -- Score card ---------------------------------------------------------
    w(f"| Field | Value |")
    w(f"|-------|-------|")
    w(f"| **URL** | {url} |")
    w(f"| **Score** | {format_score(score)} / 100 {grade_emoji(grade)} |")
    w(f"| **Grade** | {grade} |")
    w(f"| **Word Count** | {word_count:,} |")
    w(f"| **Content Type** | {content_type} |")
    w(f"| **Scoring Method** | {method} |")
    if model:
        w(f"| **AI Model** | {provider}/{model} |")
    w(f"| **Audited** | {timestamp[:19] if timestamp else 'n/a'} |")
    w("")

    if assessment:
        w(f"> {assessment}")
        w("")

    # -- Screenshot ---------------------------------------------------------
    if screenshot_file:
        w("## Page Screenshot")
        w("")
        w(f"![Screenshot of {label}]({screenshot_file})")
        w("")

    # -- Visual Analysis (AI-written from screenshot) -----------------------
    if visual_analysis:
        w("## Visual Analysis")
        w("")
        design_score = visual_analysis.get("design_score")
        if design_score is not None:
            w(f"**Design Score:** {design_score} / 10")
            w("")
        for field, heading in [
            ("layout_quality", "Layout Quality"),
            ("visual_hierarchy", "Visual Hierarchy"),
            ("readability", "Readability"),
            ("trust_signals", "Trust Signals"),
            ("mobile_readiness", "Mobile Readiness"),
            ("scannability", "Scannability"),
        ]:
            val = visual_analysis.get(field)
            if val:
                w(f"**{heading}:** {val}")
                w("")
        design_recs = visual_analysis.get("design_recommendations", [])
        if design_recs:
            w("**Design Recommendations:**")
            w("")
            for rec in design_recs:
                w(f"- {rec}")
            w("")

    # -- Executive Summary (AI-written) ------------------------------------
    if executive_summary:
        w("## Executive Summary")
        w("")
        w(executive_summary)
        w("")

    # -- Priority Actions ---------------------------------------------------
    if priority_actions:
        w("## Priority Action Plan")
        w("")
        w("The top changes that will have the biggest impact on AI citability:")
        w("")
        for i, action in enumerate(priority_actions, 1):
            title = action.get("title", "")
            impact = action.get("impact", "")
            effort = action.get("effort", "")
            desc = action.get("description", "")
            impact_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(impact, "⚪")
            effort_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(effort, "⚪")
            w(f"### {i}. {title}")
            w("")
            w(f"**Impact:** {impact_icon} {impact.title()}  |  **Effort:** {effort_icon} {effort.title()}")
            w("")
            w(desc)
            w("")

    # -- Sample Improvements (AI-written before/after) ----------------------
    if sample_improvements:
        w("## Sample Improvements")
        w("")
        w("Concrete before/after examples you can adapt for your site:")
        w("")
        for j, sample in enumerate(sample_improvements, 1):
            section = sample.get("section", f"Example {j}")
            current = sample.get("current", "")
            improved = sample.get("improved", "")
            addressed = sample.get("patterns_addressed", [])

            w(f"### {j}. {section}")
            w("")
            if addressed:
                tags = ", ".join(f"`{p.replace('_', ' ').title()}`" for p in addressed)
                w(f"**Patterns addressed:** {tags}")
                w("")
            if current:
                w("**Before (current):**")
                w("")
                w(f"> {current}")
                w("")
            if improved:
                w("**After (improved):**")
                w("")
                w(f"> {improved}")
                w("")

    # -- Pattern breakdown --------------------------------------------------
    w("## Detailed Pattern Scores")
    w("")

    sorted_patterns = sorted(
        patterns.items(),
        key=lambda kv: kv[1].get("max", 0),
        reverse=True,
    )

    for name, p in sorted_patterns:
        s = float(p.get("score", 0))
        mx = float(p.get("max", 0))
        det = "✅ Detected" if p.get("detected") else "❌ Not detected"
        display = name.replace("_", " ").title()
        pct = int(s / mx * 100) if mx else 0

        w(f"### {display} — {format_score(s)} / {format_score(mx)} ({pct}%)")
        w("")
        w(f"{score_bar(s, mx, 25)}  {det}")
        w("")

        evidence = p.get("evidence", [])
        if evidence:
            w("**Evidence:**")
            w("")
            for ev in evidence:
                w(f"- {ev}")
            w("")

        rec = p.get("recommendation", "")
        if rec:
            w(f"**Recommendation:** {rec}")
            w("")

    # -- Gap Analysis -------------------------------------------------------
    if gaps:
        w("## Gap Analysis")
        w("")
        w("| Severity | Pattern | Score | Max | Recommendation |")
        w("|:--------:|---------|------:|----:|----------------|")
        sorted_gaps = sorted(gaps, key=lambda g: {"high": 0, "medium": 1, "low": 2}.get(g.get("severity", "low"), 3))
        for g in sorted_gaps:
            sev = f"{severity_icon(g.get('severity', ''))} {g.get('severity', '').title()}"
            cat = g.get("category", "").replace("_", " ").title()
            desc = g.get("description", "")
            ps = format_score(g.get("pattern_score", 0))
            pm = format_score(g.get("pattern_max", 0))
            w(f"| {sev} | {cat} | {ps} | {pm} | {desc} |")
        w("")

    w("---")
    w(f"*Generated by AIEO • {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    w("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def render_summary_report(reports: list[dict]) -> str:
    """Render a combined markdown summary across all sites."""
    lines = []
    w = lines.append

    successful = [r for r in reports if r.get("status") == "success"]
    failed = [r for r in reports if r.get("status") != "success"]

    scores = [float(r["score"]) for r in successful]
    avg_score = sum(scores) / len(scores) if scores else 0
    best = max(successful, key=lambda r: float(r["score"]), default=None)
    worst = min(successful, key=lambda r: float(r["score"]), default=None)

    w("# AIEO Audit Summary Report")
    w("")
    w(f"**{len(reports)} sites audited** on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    w("")

    # -- Overview stats -----------------------------------------------------
    w("## Overview")
    w("")
    w(f"| Metric | Value |")
    w(f"|--------|-------|")
    w(f"| Sites Audited | {len(reports)} |")
    w(f"| Successful | {len(successful)} |")
    w(f"| Failed | {len(failed)} |")
    w(f"| Average Score | {format_score(avg_score)} / 100 |")
    if best:
        w(f"| Highest Score | {format_score(best['score'])} — {site_label(best['url'])} |")
    if worst:
        w(f"| Lowest Score | {format_score(worst['score'])} — {site_label(worst['url'])} |")
    scoring_method = successful[0].get("scoring_method", "?") if successful else "?"
    model = successful[0].get("model", "") if successful else ""
    if model:
        w(f"| AI Model | {model} |")
    w("")

    # -- Leaderboard --------------------------------------------------------
    w("## Site Rankings")
    w("")
    w("| Rank | Site | Score | Grade | Words | Gaps | Method |")
    w("|-----:|------|------:|:-----:|------:|-----:|--------|")

    ranked = sorted(successful, key=lambda r: float(r["score"]), reverse=True)
    for i, r in enumerate(ranked, 1):
        label = site_label(r["url"])
        g = grade_emoji(r["grade"])
        gap_count = len(r.get("gaps", []))
        w(f"| {i} | [{label}]({r['url']}) | {format_score(r['score'])} | {g} {r['grade']} | {r['word_count']:,} | {gap_count} | {r.get('scoring_method', '?')} |")
    w("")

    if failed:
        w("### Failed Sites")
        w("")
        for r in failed:
            w(f"- {r['url']} — {r.get('error', 'unknown error')}")
        w("")

    # -- Per-site summaries with priority actions ---------------------------
    w("## Site-by-Site Highlights")
    w("")
    for r in ranked:
        label = site_label(r["url"])
        fname = r.get("_source_file", "").replace(".json", ".md")
        score_val = format_score(r["score"])
        grade_val = r.get("grade", "?")
        assessment = r.get("overall_assessment", "")
        priority_actions = r.get("priority_actions", [])

        w(f"### [{label}]({fname}) — {score_val}/100 ({grade_emoji(grade_val)} {grade_val})")
        w("")
        if assessment:
            w(f"> {assessment}")
            w("")
        if priority_actions:
            w("**Top actions:**")
            w("")
            for action in priority_actions[:3]:
                title = action.get("title", "")
                impact = action.get("impact", "")
                impact_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(impact, "⚪")
                w(f"- {impact_icon} **{title}** — {action.get('description', '')}")
            w("")

    # -- Score distribution -------------------------------------------------
    w("## Score Distribution")
    w("")
    w("```")
    bucket_labels = ["0-19", "20-39", "40-59", "60-79", "80-100"]
    buckets = [0] * 5
    for s in scores:
        idx = min(int(s // 20), 4)
        buckets[idx] += 1

    max_b = max(buckets) if buckets else 1
    for label_b, count in zip(bucket_labels, buckets):
        bar = "█" * round(count / max_b * 30) if max_b else ""
        w(f"  {label_b:>6}  {bar} {count}")
    w("```")
    w("")

    # -- Cross-site pattern heatmap -----------------------------------------
    w("## Pattern Heatmap")
    w("")
    w("How each pattern scores across all sites (percentage of max):")
    w("")

    # Collect all pattern names
    all_patterns: dict[str, list[float]] = {}
    for r in successful:
        for pname, pdata in r.get("pattern_scores", {}).items():
            pct = (float(pdata["score"]) / float(pdata["max"]) * 100) if pdata.get("max") else 0
            all_patterns.setdefault(pname, []).append(pct)

    # Sort by avg score ascending (weakest first)
    sorted_patterns = sorted(all_patterns.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))

    header_sites = " | ".join(site_label(r["url"])[:12] for r in ranked)
    w(f"| Pattern | Avg | {header_sites} |")
    w(f"|---------|----:|{'|'.join([' ---:'] * len(ranked))} |")

    for pname, _ in sorted_patterns:
        display = pname.replace("_", " ").title()
        row_vals = []
        for r in ranked:
            pd = r.get("pattern_scores", {}).get(pname, {})
            pct = (float(pd.get("score", 0)) / float(pd.get("max", 1)) * 100) if pd.get("max") else 0
            row_vals.append(f"{pct:.0f}%")
        avg_pct = sum(all_patterns[pname]) / len(all_patterns[pname])
        w(f"| {display} | {avg_pct:.0f}% | {' | '.join(row_vals)} |")
    w("")

    # -- Most common gaps ---------------------------------------------------
    w("## Most Common Gaps")
    w("")
    gap_freq: dict[str, dict] = {}
    for r in successful:
        for g in r.get("gaps", []):
            cat = g.get("category", "unknown")
            if cat not in gap_freq:
                gap_freq[cat] = {"count": 0, "severity": g.get("severity", "low"), "description": g.get("description", "")}
            gap_freq[cat]["count"] += 1

    sorted_gaps = sorted(gap_freq.items(), key=lambda kv: kv[1]["count"], reverse=True)
    w("| Gap | Affected Sites | Severity | Recommendation |")
    w("|-----|---------------:|:--------:|----------------|")
    for cat, info in sorted_gaps:
        display = cat.replace("_", " ").title()
        sev = f"{severity_icon(info['severity'])} {info['severity'].title()}"
        w(f"| {display} | {info['count']} / {len(successful)} | {sev} | {info['description']} |")
    w("")

    # -- Key takeaways ------------------------------------------------------
    w("## Key Takeaways")
    w("")

    # Find universally weak patterns (avg < 30%)
    weak = [name for name, pcts in sorted_patterns if (sum(pcts) / len(pcts)) < 30]
    strong = [name for name, pcts in sorted_patterns if (sum(pcts) / len(pcts)) >= 70]

    if weak:
        w("### Weakest Patterns Across All Sites")
        w("")
        for p in weak:
            avg_pct = sum(all_patterns[p]) / len(all_patterns[p])
            display = p.replace("_", " ").title()
            w(f"- **{display}** — avg {avg_pct:.0f}% of max score")
        w("")

    if strong:
        w("### Strongest Patterns Across All Sites")
        w("")
        for p in strong:
            avg_pct = sum(all_patterns[p]) / len(all_patterns[p])
            display = p.replace("_", " ").title()
            w(f"- **{display}** — avg {avg_pct:.0f}% of max score")
        w("")

    # -- Links to individual reports ----------------------------------------
    w("## Individual Reports")
    w("")
    w("Each report includes a detailed executive summary, priority action plan, and concrete before/after content improvement examples written by AI:")
    w("")
    for r in ranked:
        label = site_label(r["url"])
        fname = r.get("_source_file", "").replace(".json", ".md")
        w(f"- [{label}]({fname}) — {format_score(r['score'])} / 100")
    w("")

    w("---")
    w(f"*Generated by AIEO • {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    w("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(input_dir: str = "reports", output_dir: str | None = None):
    """Generate markdown reports from JSON audit data."""
    inp = Path(input_dir)
    out = Path(output_dir) if output_dir else inp
    out.mkdir(parents=True, exist_ok=True)

    reports = load_site_reports(inp)
    if not reports:
        print(f"No JSON report files found in {inp}")
        return

    print(f"Found {len(reports)} site reports in {inp}")

    # Generate per-site reports
    for data in reports:
        md = render_site_report(data)
        fname = data["_source_file"].replace(".json", ".md")
        (out / fname).write_text(md)
        label = site_label(data.get("url", ""))
        print(f"  ✓ {fname:<40} {format_score(data.get('score', 0)):>5} / 100  ({label})")

    # Generate summary report
    summary_md = render_summary_report(reports)
    (out / "REPORT.md").write_text(summary_md)
    print(f"  ✓ {'REPORT.md':<40} (summary of all {len(reports)} sites)")

    print(f"\nAll reports written to {out}/")


def main():
    parser = argparse.ArgumentParser(description="Generate AIEO markdown reports from JSON audit data")
    parser.add_argument("--input", default="reports", help="Directory containing JSON results (default: reports)")
    parser.add_argument("--output", default=None, help="Output directory for markdown files (default: same as input)")
    args = parser.parse_args()
    generate(input_dir=args.input, output_dir=args.output)


if __name__ == "__main__":
    main()
