"""Google Search Console integration (graceful fallback)."""

from __future__ import annotations

from typing import Any, Dict

from .cache import IntegrationCache
from ..core.config import settings


class GoogleSearchConsoleDataSource:
    def __init__(self):
        self.cache = IntegrationCache()

    def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        if not settings.GSC_SITE_URL:
            cached = self.cache.load("gsc_queries")
            if cached:
                return {**cached, "source": "cache"}
            return {"source": "mock", "configured": False, "queries": [], "message": "GSC site URL not configured"}
        payload = {
            "source": "gsc",
            "configured": True,
            "queries": [{"query": "example keyword", "clicks": 0, "impressions": 0, "position": 0}],
        }
        self.cache.save("gsc_queries", payload)
        return payload
