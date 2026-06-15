"""Research workflow service."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .ai_service import AIService
from .prompt_loader import PromptLoader
from .workspace_service import WorkspaceService
from ..core.config import workspace_root


class ResearchService:
    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        prompt_loader: Optional[PromptLoader] = None,
        workspace: Optional[WorkspaceService] = None,
    ):
        self.ai_service = ai_service or AIService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.workspace = workspace or WorkspaceService(workspace_root())

    async def create_brief(self, topic: str, model: Optional[str] = None) -> Dict:
        self.workspace.initialize()
        prompt_item = self.prompt_loader.get_collection_item("commands", "research")
        base_prompt = (
            prompt_item["body"] if prompt_item else "Create a content research brief."
        )
        prompt = f"{base_prompt}\n\nTopic: {topic}\n\nReturn markdown."
        try:
            content = await self.ai_service.generate(prompt=prompt, model=model)
        except Exception:
            content = f"# Research Brief: {topic}\n\n## Primary keyword\n\n- {topic}\n\n## Recommended outline\n\n- Introduction\n- Main sections\n- FAQ\n"
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        path = f"research/brief-{topic.lower().replace(' ', '-')}-{stamp}.md"
        self.workspace.write_file(path, content)
        return {"path": path, "content": content}
