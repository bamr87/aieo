"""Article writing workflow service."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .agent_runner import AgentRunner
from .ai_service import AIService
from .prompt_loader import PromptLoader
from .workspace_service import WorkspaceService
from ..core.config import workspace_root


class WriteService:
    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        prompt_loader: Optional[PromptLoader] = None,
        workspace: Optional[WorkspaceService] = None,
        agent_runner: Optional[AgentRunner] = None,
    ):
        self.ai_service = ai_service or AIService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.workspace = workspace or WorkspaceService(workspace_root())
        self.agent_runner = agent_runner or AgentRunner(
            prompt_loader=self.prompt_loader,
            ai_service=self.ai_service,
            workspace_service=self.workspace,
        )

    async def write(self, topic: str, brief_path: Optional[str] = None, model: Optional[str] = None) -> Dict:
        self.workspace.initialize()
        brief = ""
        if brief_path:
            try:
                brief = self.workspace.read_file(brief_path)["content"]
            except FileNotFoundError:
                brief = ""
        prompt_item = self.prompt_loader.get_collection_item("commands", "write")
        base_prompt = prompt_item["body"] if prompt_item else "Write a long-form article."
        prompt = f"{base_prompt}\n\nTopic: {topic}\n\nResearch brief:\n{brief}\n\nReturn markdown."
        try:
            content = await self.ai_service.generate(prompt=prompt, model=model)
        except Exception:
            content = f"# {topic}\n\n## Introduction\n\nDraft generated without AI provider.\n"

        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        draft_path = f"drafts/{topic.lower().replace(' ', '-')}-{stamp}.md"
        self.workspace.write_file(draft_path, content)

        agent_results = {}
        for agent in ["seo-optimizer", "meta-creator", "internal-linker", "keyword-mapper"]:
            try:
                agent_results[agent] = await self.agent_runner.run_agent(agent, content, model=model)
            except Exception as exc:
                agent_results[agent] = {"error": str(exc)}
        return {"path": draft_path, "content": content, "agents": agent_results}
