"""Site snapshot capability: crawl a Jekyll/static site into a cached, offline,
multi-format report (text, json, markdown, html, pdf, bundle).

Public surface — every other entry point (REST, MCP, CLI, standalone script)
imports from here::

    from app.services.site_snapshot import SiteSnapshotService, CrawlConfig
"""

from .config import CrawlConfig
from .model import PageRecord, SiteSnapshot
from .snapshot_service import SiteSnapshotService

__all__ = ["SiteSnapshotService", "CrawlConfig", "SiteSnapshot", "PageRecord"]
