"""Rewrite workflow service."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .ai_service import AIService
from .prompt_loader import PromptLoader
from .workspace_service import WorkspaceService
from ..core.config import workspace_root


class RewriteService:
    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        prompt_loader: Optional[PromptLoader] = None,
        workspace: Optional[WorkspaceService] = None,
    ):
        self.ai_service = ai_service or AIService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.workspace = workspace or WorkspaceService(workspace_root())

    async def rewrite(self, source_path: str, model: Optional[str] = None) -> Dict:
        self.workspace.initialize()
        source = self.workspace.read_file(source_path)["content"]
        prompt_item = self.prompt_loader.get_collection_item("commands", "rewrite")
        base_prompt = prompt_item["body"] if prompt_item else "Rewrite this content."
        prompt = f"{base_prompt}\n\nContent:\n{source}\n\nReturn markdown."
        try:
            rewritten = await self.ai_service.generate(prompt=prompt, model=model)
        except Exception:
            rewritten = source
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        out_path = f"rewrites/{Pathish.basename_no_ext(source_path)}-rewrite-{stamp}.md"
        self.workspace.write_file(out_path, rewritten)
        return {"path": out_path, "content": rewritten}


class Pathish:
    @staticmethod
    def basename_no_ext(rel_path: str) -> str:
        name = rel_path.split("/")[-1]
        return name.rsplit(".", 1)[0]
