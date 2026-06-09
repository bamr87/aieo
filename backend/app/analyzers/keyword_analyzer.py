"""Keyword density and placement analysis."""

from __future__ import annotations

from typing import Dict, List

from .text_utils import top_terms, word_count, words


class KeywordAnalyzer:
    def analyze(
        self,
        text: str,
        primary_keyword: str | None = None,
        secondary_keywords: List[str] | None = None,
    ) -> Dict:
        tokens = words(text)
        wc = max(1, word_count(text))
        secondary_keywords = secondary_keywords or []

        def density(keyword: str) -> Dict:
            if not keyword:
                return {"keyword": "", "count": 0, "density": 0.0}
            kw = keyword.lower()
            count = sum(1 for t in tokens if t == kw or kw in t)
            return {"keyword": keyword, "count": count, "density": round((count / wc) * 100, 2)}

        top = top_terms(text, min_len=4, limit=15)
        stuffing_risk = any((count / wc) > 0.05 for _, count in top)
        return {
            "word_count": wc,
            "primary": density(primary_keyword or ""),
            "secondary": [density(k) for k in secondary_keywords],
            "lsi_keywords": [term for term, _ in top[:10]],
            "topic_clusters": [[term for term, _ in top[:5]], [term for term, _ in top[5:10]]],
            "keyword_stuffing_risk": stuffing_risk,
            "distribution": {
                "intro": text[: max(1, len(text) // 5)],
                "body": text[max(1, len(text) // 5): max(1, len(text) * 4 // 5)],
                "outro": text[max(1, len(text) * 4 // 5):],
            },
        }
