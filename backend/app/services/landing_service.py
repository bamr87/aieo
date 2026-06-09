"""Landing page workflow service."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from ..analyzers import LandingPageScorer
from .ai_service import AIService
from .workspace_service import WorkspaceService
from ..core.config import workspace_root


class LandingService:
    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        workspace: Optional[WorkspaceService] = None,
    ):
        self.ai_service = ai_service or AIService()
        self.workspace = workspace or WorkspaceService(workspace_root())
        self.scorer = LandingPageScorer()

    async def write(self, topic: str, model: Optional[str] = None) -> Dict:
        prompt = f"Write a conversion-focused landing page in markdown for: {topic}"
        try:
            content = await self.ai_service.generate(prompt, model=model)
        except Exception:
            content = f"# {topic}\n\n## Why this matters\n\n## CTA\n\nGet started.\n"
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        path = f"landing-pages/{topic.lower().replace(' ', '-')}-{stamp}.md"
        self.workspace.write_file(path, content)
        return {"path": path, "content": content}

    def audit(self, content: str) -> Dict:
        return self.scorer.score(content)

    async def research(self, topic: str, model: Optional[str] = None) -> Dict:
        prompt = f"Provide landing page research for: {topic}. Return markdown."
        try:
            content = await self.ai_service.generate(prompt, model=model)
        except Exception:
            content = f"# Landing Research: {topic}\n\n- Audience\n- Offer\n- Objections\n"
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        path = f"audits/landing-research-{topic.lower().replace(' ', '-')}-{stamp}.md"
        self.workspace.write_file(path, content)
        return {"path": path, "content": content}

    async def competitor(self, url: str, model: Optional[str] = None) -> Dict:
        prompt = f"Analyze this competitor landing page URL and return concise findings: {url}"
        try:
            result = await self.ai_service.generate(prompt, model=model)
        except Exception:
            result = f"Competitor review placeholder for {url}"
        return {"url": url, "analysis": result}
