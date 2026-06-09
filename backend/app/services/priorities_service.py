"""Content prioritization service."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..analyzers import OpportunityScorer
from .data_service import DataService


class PrioritiesService:
    def __init__(self, data_service: Optional[DataService] = None):
        self.data_service = data_service or DataService()
        self.scorer = OpportunityScorer()

    def build_priorities(self) -> Dict:
        gsc = self.data_service.get_gsc_queries()
        queue: List[Dict] = []
        for row in gsc.get("queries", []):
            scored = self.scorer.score(
                position=float(row.get("position", 50)),
                impressions=int(row.get("impressions", 0)),
                ctr=float(row.get("ctr", 0)),
                trend_delta=0.0,
                business_priority=0.5,
            )
            queue.append({"query": row.get("query"), "opportunity_score": scored["score"], "components": scored["components"]})
        queue.sort(key=lambda item: item["opportunity_score"], reverse=True)
        return {"queue": queue, "quick_wins": [q for q in queue if q["opportunity_score"] >= 60][:10]}
