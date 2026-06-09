"""Google Analytics integration (graceful fallback)."""

from __future__ import annotations

from typing import Any, Dict

from .cache import IntegrationCache
from ..core.config import settings


class GoogleAnalyticsDataSource:
    def __init__(self):
        self.cache = IntegrationCache()

    def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        if not settings.GA4_PROPERTY_ID:
            cached = self.cache.load("ga_top_pages")
            if cached:
                return {**cached, "source": "cache"}
            return {
                "source": "mock",
                "configured": False,
                "top_pages": [],
                "message": "GA4 property not configured",
            }
        # Placeholder for GA4 API call wiring
        payload = {
            "source": "ga4",
            "configured": True,
            "top_pages": [
                {"url": "/blog/example", "sessions": 0, "engagement_rate": 0.0},
            ],
        }
        self.cache.save("ga_top_pages", payload)
        return payload
