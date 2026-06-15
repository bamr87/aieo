"""DataForSEO integration (graceful fallback)."""

from __future__ import annotations

from typing import Any, Dict

from .cache import IntegrationCache
from ..core.config import settings


class DataForSEODataSource:
    def __init__(self):
        self.cache = IntegrationCache()

    def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        if not (settings.DATAFORSEO_LOGIN and settings.DATAFORSEO_PASSWORD):
            cached = self.cache.load("dfs_serp")
            if cached:
                return {**cached, "source": "cache"}
            return {
                "source": "mock",
                "configured": False,
                "serp": [],
                "message": "DataForSEO credentials not configured",
            }
        payload = {
            "source": "dataforseo",
            "configured": True,
            "serp": [{"keyword": kwargs.get("keyword", "example"), "top_urls": []}],
        }
        self.cache.save("dfs_serp", payload)
        return payload
