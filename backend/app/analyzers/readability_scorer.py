"""Readability metrics for markdown/html text."""

from __future__ import annotations

import re
from typing import Dict

from .text_utils import avg_sentence_length, sentence_count, word_count


_PASSIVE_RE = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+\w+ed\b", re.IGNORECASE)


class ReadabilityScorer:
    def score(self, text: str) -> Dict:
        wc = max(1, word_count(text))
        sc = max(1, sentence_count(text))
        asl = avg_sentence_length(text)
        passive = len(_PASSIVE_RE.findall(text))
        passive_ratio = round((passive / sc) * 100, 1)
        # Lightweight readability approximation (higher is easier)
        ease = round(max(0, min(100, 110 - (asl * 2.2))), 1)
        grade_level = round(max(1, min(18, 16 - (ease / 8))), 1)
        return {
            "score": round(max(0, min(100, ease)), 1),
            "flesch_reading_ease": ease,
            "flesch_kincaid_grade": grade_level,
            "average_sentence_length": round(asl, 1),
            "sentence_count": sc,
            "word_count": wc,
            "passive_voice_ratio": passive_ratio,
        }
