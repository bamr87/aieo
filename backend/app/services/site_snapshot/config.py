"""Tunable configuration for a site snapshot crawl.

A single dataclass holds every knob with safe defaults so callers can pass
nothing, and the surfaces (REST/MCP/CLI) can build one from a loose JSON dict.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

try:  # settings is available under the full and the CI dependency sets
    from ...core.config import settings

    _MAX_BYTES = int(settings.MAX_CONTENT_SIZE_BYTES)
except Exception:  # pragma: no cover - defensive, keep the package importable
    _MAX_BYTES = 10 * 1024 * 1024


# Jekyll themes generate a lot of pagination / taxonomy noise that is not real
# content. These path prefixes are skipped from the crawl frontier by default.
DEFAULT_DENIED_PREFIXES: List[str] = [
    "/assets/",
    "/tag/",
    "/tags/",
    "/category/",
    "/categories/",
    "/page/",
]


@dataclass
class CrawlConfig:
    """Knobs for a crawl. All optional; defaults are polite and offline-friendly."""

    max_pages: int = 500
    max_depth: int = 6
    max_link_pages: int = 200  # separate budget for BFS-discovered (non-sitemap) pages
    max_bytes_per_page: int = field(default_factory=lambda: _MAX_BYTES)
    delay_seconds: float = 0.25  # polite default; robots Crawl-delay can raise it
    timeout: float = 30.0
    respect_robots: bool = True
    use_cache: bool = True
    refresh: bool = False  # ignore validators + hash short-circuit, always re-fetch
    ttl_seconds: int = 0  # >0 skips revalidation for entries younger than this
    include_external: bool = False  # record off-host links, never crawl them
    include_assets: bool = False  # download + inline images as data URIs in HTML/bundle
    strip_boilerplate: bool = True  # extract main content only (drop nav/footer/chrome)
    max_assets: int = 200
    max_asset_bytes: int = 2 * 1024 * 1024
    denied_path_prefixes: List[str] = field(
        default_factory=lambda: list(DEFAULT_DENIED_PREFIXES)
    )

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "CrawlConfig":
        """Build a config from a loose dict, ignoring unknown keys."""
        if not data:
            return cls()
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known and v is not None}
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
