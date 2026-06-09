"""Opportunity scoring for content prioritization."""

from __future__ import annotations

from typing import Dict


class OpportunityScorer:
    def score(
        self,
        *,
        position: float = 50.0,
        impressions: int = 0,
        ctr: float = 0.0,
        trend_delta: float = 0.0,
        business_priority: float = 0.5,
    ) -> Dict:
        position_score = max(0, min(100, (100 - min(position, 100))))
        impressions_score = min(100, impressions / 100)
        ctr_gap_score = max(0, min(100, 100 - (ctr * 100)))
        trend_score = max(0, min(100, 50 + trend_delta))
        business_score = max(0, min(100, business_priority * 100))
        overall = round(
            (position_score * 0.3)
            + (impressions_score * 0.25)
            + (ctr_gap_score * 0.2)
            + (trend_score * 0.15)
            + (business_score * 0.1),
            1,
        )
        return {
            "score": overall,
            "components": {
                "position": position_score,
                "impressions": impressions_score,
                "ctr_gap": ctr_gap_score,
                "trend": trend_score,
                "business_priority": business_score,
            },
        }
