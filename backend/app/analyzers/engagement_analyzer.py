"""Engagement pattern analysis."""

from __future__ import annotations

import re
from typing import Dict


class EngagementAnalyzer:
    def analyze(self, text: str) -> Dict:
        question_count = len(re.findall(r"\?", text))
        cta_count = len(
            re.findall(
                r"\b(try|start|book|download|learn more|contact)\b", text.lower()
            )
        )
        example_count = len(
            re.findall(r"\b(example|for instance|case study)\b", text.lower())
        )
        score = min(100, question_count * 8 + cta_count * 12 + example_count * 10)
        return {
            "score": score,
            "questions": question_count,
            "ctas": cta_count,
            "examples": example_count,
        }
