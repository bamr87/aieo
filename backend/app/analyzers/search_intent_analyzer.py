"""Simple search intent classifier."""

from __future__ import annotations

from typing import Dict


class SearchIntentAnalyzer:
    KEYWORDS = {
        "informational": ["what", "how", "guide", "learn", "tips", "best practices"],
        "navigational": ["login", "official", "website", "pricing page", "docs"],
        "transactional": ["buy", "purchase", "demo", "trial", "subscribe", "book"],
        "commercial": ["vs", "compare", "review", "alternatives", "top"],
    }

    def analyze(self, query_or_content: str) -> Dict:
        text = query_or_content.lower()
        scores = {intent: 0 for intent in self.KEYWORDS}
        for intent, terms in self.KEYWORDS.items():
            for term in terms:
                if term in text:
                    scores[intent] += 1
        intent = max(scores, key=scores.get)
        total = sum(scores.values()) or 1
        confidence = round((scores[intent] / total) * 100, 1)
        return {"intent": intent, "confidence": confidence, "signals": scores}
