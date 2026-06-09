"""Scrub AI-watermark style artifacts from content."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .ai_service import AIService
from .prompt_loader import PromptLoader
from .workspace_service import WorkspaceService
from ..core.config import workspace_root


class ScrubService:
    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        prompt_loader: Optional[PromptLoader] = None,
        workspace: Optional[WorkspaceService] = None,
    ):
        self.ai_service = ai_service or AIService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.workspace = workspace or WorkspaceService(workspace_root())

    async def scrub(self, content: str, model: Optional[str] = None) -> Dict:
        self.workspace.initialize()
        prompt_item = self.prompt_loader.get_collection_item("commands", "scrub")
        base_prompt = prompt_item["body"] if prompt_item else "Rewrite to sound natural."
        prompt = f"{base_prompt}\n\nContent:\n{content}"
        try:
            cleaned = await self.ai_service.generate(prompt=prompt, model=model)
        except Exception:
            cleaned = content.replace(" - ", ", ").replace("—", ",")
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        path = f"drafts/scrubbed-{stamp}.md"
        self.workspace.write_file(path, cleaned)
        return {"path": path, "content": cleaned}
