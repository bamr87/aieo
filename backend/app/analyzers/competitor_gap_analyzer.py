"""Detect high-level topical gaps against competitor notes."""

from __future__ import annotations

from typing import Dict, List


class CompetitorGapAnalyzer:
    def analyze(self, text: str, competitor_topics: List[str] | None = None) -> Dict:
        competitor_topics = competitor_topics or []
        lower = text.lower()
        missing = [topic for topic in competitor_topics if topic.lower() not in lower]
        return {
            "missing_topics": missing,
            "gap_count": len(missing),
            "recommendation": "Add sections for missing high-intent topics." if missing else "Coverage looks complete.",
        }
