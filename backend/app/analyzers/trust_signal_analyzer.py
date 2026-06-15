"""Detect trust signals in page copy."""

from __future__ import annotations

import re
from typing import Dict


class TrustSignalAnalyzer:
    def analyze(self, text: str) -> Dict:
        lower = text.lower()
        testimonial_hits = len(re.findall(r"\btestimonial|review|case study\b", lower))
        social_proof_hits = len(re.findall(r"\bcustomers|companies|teams\b", lower))
        risk_reversal_hits = len(
            re.findall(r"\bguarantee|cancel anytime|refund\b", lower)
        )
        score = min(
            100,
            testimonial_hits * 20 + social_proof_hits * 10 + risk_reversal_hits * 20,
        )
        return {
            "score": score,
            "testimonials": testimonial_hits,
            "social_proof": social_proof_hits,
            "risk_reversal": risk_reversal_hits,
        }
