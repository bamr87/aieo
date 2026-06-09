"""Integration interfaces."""

from __future__ import annotations

from typing import Any, Dict, Protocol


class DataSource(Protocol):
    def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        """Fetch data from integration source."""
