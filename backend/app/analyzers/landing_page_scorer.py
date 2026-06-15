"""Composite landing page CRO score."""

from __future__ import annotations

from typing import Dict

from .above_fold_analyzer import AboveFoldAnalyzer
from .cta_analyzer import CTAAnalyzer
from .trust_signal_analyzer import TrustSignalAnalyzer


class LandingPageScorer:
    def __init__(self):
        self.above_fold = AboveFoldAnalyzer()
        self.cta = CTAAnalyzer()
        self.trust = TrustSignalAnalyzer()

    def score(self, text: str) -> Dict:
        above = self.above_fold.analyze(text)
        cta = self.cta.analyze(text)
        trust = self.trust.analyze(text)
        total = round(
            (above["score"] * 0.4) + (cta["score"] * 0.35) + (trust["score"] * 0.25), 1
        )
        return {"score": total, "above_fold": above, "cta": cta, "trust": trust}
