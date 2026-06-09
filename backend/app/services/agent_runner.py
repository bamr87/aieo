"""Run specialized prompt agents against content."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .ai_service import AIService
from .prompt_loader import PromptLoader
from .workspace_service import WorkspaceService
from ..core.config import workspace_root


class AgentRunner:
    def __init__(
        self,
        prompt_loader: Optional[PromptLoader] = None,
        ai_service: Optional[AIService] = None,
        workspace_service: Optional[WorkspaceService] = None,
    ):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.ai_service = ai_service or AIService()
        self.workspace = workspace_service or WorkspaceService(workspace_root())

    def _collect_context(self) -> Dict[str, str]:
        context_data: Dict[str, str] = {}
        for rel in [
            "context/brand-voice.md",
            "context/style-guide.md",
            "context/target-keywords.md",
            "context/internal-links-map.md",
            "context/competitor-analysis.md",
        ]:
            try:
                context_data[rel] = self.workspace.read_file(rel)["content"]
            except FileNotFoundError:
                continue
        return context_data

    async def run_agent(
        self,
        agent_name: str,
        content: str,
        extra_inputs: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt_item = self.prompt_loader.get_collection_item("agents", agent_name)
        if not prompt_item:
            raise ValueError(f"Unknown agent: {agent_name}")
        context_data = self._collect_context()
        payload = {
            "agent": prompt_item["name"],
            "display_name": prompt_item["display_name"],
            "content": content,
            "context": context_data,
            "extra_inputs": extra_inputs or {},
        }
        prompt = (
            f"{prompt_item['body']}\n\n"
            "Return JSON only.\n\n"
            f"Input:\n{json.dumps(payload, indent=2)}"
        )
        raw = await self.ai_service.generate(prompt=prompt, model=model)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw_output": raw}
        return {"agent": agent_name, "result": parsed}
