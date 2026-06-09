"""Overall SEO quality rating."""

from __future__ import annotations

import re
from typing import Dict

from .text_utils import word_count


class SEOQualityRater:
    def rate(self, text: str) -> Dict:
        wc = word_count(text)
        has_h1 = "# " in text
        has_h2 = "## " in text
        has_links = "http://" in text or "https://" in text
        has_meta = "meta title" in text.lower() or "meta description" in text.lower()
        has_list = "- " in text or "1. " in text
        score = 0
        score += 20 if wc >= 1200 else max(0, int((wc / 1200) * 20))
        score += 15 if has_h1 else 0
        score += 15 if has_h2 else 0
        score += 15 if has_links else 0
        score += 15 if has_meta else 0
        score += 20 if has_list else 0
        score = min(100, score)
        return {
            "score": score,
            "category_breakdown": {
                "content": min(20, int((wc / 1200) * 20)),
                "structure": 30 if (has_h1 and has_h2) else (15 if has_h1 or has_h2 else 0),
                "links": 15 if has_links else 0,
                "meta": 15 if has_meta else 0,
                "readability_structure": 20 if has_list else 0,
            },
            "critical_issues": [] if score >= 70 else ["Missing key SEO elements"],
            "warnings": [] if score >= 50 else ["Content likely under-optimized for search"],
        }
