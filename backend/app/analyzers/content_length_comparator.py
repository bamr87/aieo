"""Compare content length against target ranges."""

from __future__ import annotations

from typing import Dict, List

from .text_utils import word_count


class ContentLengthComparator:
    def compare(
        self, text: str, competitor_word_counts: List[int] | None = None
    ) -> Dict:
        competitor_word_counts = competitor_word_counts or [
            1200,
            1500,
            1800,
            2200,
            2600,
        ]
        wc = word_count(text)
        ordered = sorted(competitor_word_counts)
        median = ordered[len(ordered) // 2]
        p75 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.75))]
        gap = median - wc
        return {
            "word_count": wc,
            "competitor_median": median,
            "competitor_p75": p75,
            "optimal_target": p75,
            "gap_to_target": gap,
            "recommendation": (
                "Expand depth with examples and FAQs."
                if wc < median
                else "Length is competitive."
            ),
        }
