"""Site context capability: crawl a URL and N levels below it into a contextual
dataset — a link map, per-page content and metadata, a presentation profile
(styles, imagery, animation), SEO facts, and an analysis produced by looping the
pages through the Claude Code CLI over OAuth.

Public surface — every entry point (REST, MCP, CLI, standalone script) imports
from here::

    from app.services.site_context import SiteContextService, ContextConfig
"""

from .config import ContextConfig
from .context_service import SiteContextService
from .model import ContextNode, SiteContext

__all__ = ["SiteContextService", "ContextConfig", "SiteContext", "ContextNode"]
