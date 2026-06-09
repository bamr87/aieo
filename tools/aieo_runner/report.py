"""Markdown summary report for headless runner results."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def write_report_md(output_dir: Path, rows: List[Dict[str, Any]], title: str = "AIEO markdown report") -> Path:
    """Write REPORT.md under output_dir. Each row: file, status, score, grade, gap_count, method, error."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "REPORT.md"
    lines: List[str] = [
        f"# {title}",
        "",
        f"_Generated: {datetime.now(timezone.utc).isoformat()}_",
        "",
        "| File | Status | Score | Grade | Gaps | Method | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        notes = r.get("error") or r.get("notes") or ""
        lines.append(
            "| `{file}` | {status} | {score} | {grade} | {gaps} | {method} | {notes} |".format(
                file=r.get("file", ""),
                status=r.get("status", ""),
                score=r.get("score", "") if r.get("score") is not None else "",
                grade=r.get("grade", "") if r.get("grade") is not None else "",
                gaps=r.get("gap_count", "") if r.get("gap_count") is not None else "",
                method=r.get("method", "") or "",
                notes=str(notes).replace("|", "\\|")[:200],
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
