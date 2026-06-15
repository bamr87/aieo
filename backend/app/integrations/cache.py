"""Simple JSON file cache for integrations."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ..core.config import workspace_root


class IntegrationCache:
    def __init__(self):
        self.cache_dir = workspace_root() / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        path = self.cache_dir / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
