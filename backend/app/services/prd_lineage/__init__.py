"""PRD lineage: search a product repo, inventory PRD elements, align witnesses.

Public surface — REST, MCP, CLI, and the standalone script import from here::

    from app.services.prd_lineage import PrdLineageService, PrdConfig
"""

from .config import PrdConfig
from .model import PrdInventory, SourceNode
from .prd_service import PrdLineageService

__all__ = ["PrdLineageService", "PrdConfig", "PrdInventory", "SourceNode"]
