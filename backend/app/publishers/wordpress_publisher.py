"""WordPress publisher implementation."""

from __future__ import annotations

from typing import Dict, Optional

import httpx

from ..core.config import settings


class WordPressPublisher:
    async def publish(self, title: str, content: str, metadata: Optional[Dict] = None) -> Dict:
        if not (settings.WP_URL and settings.WP_USERNAME and settings.WP_APP_PASSWORD):
            return {"published": False, "message": "WordPress credentials not configured"}
        endpoint = f"{settings.WP_URL.rstrip('/')}/wp-json/wp/v2/posts"
        payload = {
            "title": title,
            "content": content,
            "status": metadata.get("status", "draft") if metadata else "draft",
        }
        if metadata and metadata.get("yoast"):
            payload.update(metadata["yoast"])
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                endpoint,
                json=payload,
                auth=(settings.WP_USERNAME, settings.WP_APP_PASSWORD),
            )
        if response.status_code >= 400:
            return {"published": False, "error": response.text}
        data = response.json()
        return {"published": True, "post_id": data.get("id"), "url": data.get("link")}
