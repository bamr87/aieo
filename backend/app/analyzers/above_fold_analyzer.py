"""Landing page above-the-fold quality checks."""

from __future__ import annotations

from typing import Dict


class AboveFoldAnalyzer:
    def analyze(self, text: str) -> Dict:
        head = text[:1500].lower()
        has_value_prop = any(term in head for term in ["why", "benefit", "helps", "for teams"])
        has_cta = any(term in head for term in ["start", "book", "try", "sign up", "get started"])
        has_trust = any(term in head for term in ["trusted", "customers", "reviews", "testimonials"])
        score = (35 if has_value_prop else 0) + (35 if has_cta else 0) + (30 if has_trust else 0)
        return {"score": score, "value_prop": has_value_prop, "cta": has_cta, "trust": has_trust}
