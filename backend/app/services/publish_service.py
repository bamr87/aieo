"""Publishing orchestration service."""

from __future__ import annotations

from typing import Dict, Optional

from ..publishers import WordPressPublisher
from .workspace_service import WorkspaceService
from ..core.config import workspace_root


class PublishService:
    def __init__(self, workspace: Optional[WorkspaceService] = None):
        self.workspace = workspace or WorkspaceService(workspace_root())
        self.wp = WordPressPublisher()

    async def publish_wordpress(self, draft_path: str, title: str, metadata: Optional[Dict] = None) -> Dict:
        content = self.workspace.read_file(draft_path)["content"]
        result = await self.wp.publish(title=title, content=content, metadata=metadata or {})
        if result.get("published"):
            published_path = draft_path.replace("drafts/", "published/")
            self.workspace.write_file(published_path, content)
            result["published_path"] = published_path
        return result
