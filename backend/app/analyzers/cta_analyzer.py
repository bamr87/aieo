"""CTA effectiveness checks."""

from __future__ import annotations

import re
from typing import Dict


class CTAAnalyzer:
    def analyze(self, text: str) -> Dict:
        ctas = re.findall(r"\b(start|book|buy|subscribe|contact|try)\b", text.lower())
        unique_ctas = sorted(set(ctas))
        score = min(100, len(ctas) * 15)
        return {"score": score, "cta_count": len(ctas), "cta_variants": unique_ctas}
