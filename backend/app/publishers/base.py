"""Publisher interfaces."""

from __future__ import annotations

from typing import Dict, Protocol


class Publisher(Protocol):
    async def publish(self, title: str, content: str, metadata: Dict | None = None) -> Dict:
        """Publish content and return URL or identifier."""
