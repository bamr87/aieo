"""Checklist validation for CRO best practices."""

from __future__ import annotations

from typing import Dict


class CROChecker:
    def check(self, text: str) -> Dict:
        lower = text.lower()
        checks = {
            "headline": "# " in text,
            "cta_present": any(term in lower for term in ["start", "book", "buy", "try"]),
            "social_proof": any(term in lower for term in ["testimonial", "review", "trusted"]),
            "objection_handling": any(term in lower for term in ["faq", "questions", "pricing", "guarantee"]),
        }
        passed = sum(1 for ok in checks.values() if ok)
        return {"passed": passed, "total": len(checks), "checks": checks, "score": round((passed / len(checks)) * 100, 1)}
