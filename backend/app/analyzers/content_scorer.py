"""Humanity and quality-oriented content scoring."""

from __future__ import annotations

from typing import Dict

from .text_utils import avg_sentence_length, top_terms, word_count


class ContentScorer:
    def score(self, text: str) -> Dict:
        wc = max(1, word_count(text))
        avg_len = avg_sentence_length(text)
        unique_terms = len({term for term, _ in top_terms(text, min_len=4, limit=100)})
        specificity = min(100, int((unique_terms / 80) * 100))
        readability = max(0, min(100, int(100 - (avg_len - 18) * 2)))
        structure = 100 if "## " in text else 55
        seo = 100 if "http" in text else 50
        humanity = min(100, int((specificity * 0.5) + (readability * 0.5)))
        return {
            "score": round((humanity + specificity + structure + seo + readability) / 5, 1),
            "humanity": humanity,
            "specificity": specificity,
            "structure": structure,
            "seo": seo,
            "readability": readability,
            "word_count": wc,
        }
