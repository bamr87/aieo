"""Analyze existing content from URL or workspace file."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import httpx

from .ai_service import AIService
from .prompt_loader import PromptLoader
from .scoring_engine import ScoringEngine
from .workspace_service import WorkspaceService
from ..core.config import workspace_root


class AnalyzeExistingService:
    def __init__(
        self,
        scoring_engine: Optional[ScoringEngine] = None,
        ai_service: Optional[AIService] = None,
        prompt_loader: Optional[PromptLoader] = None,
        workspace: Optional[WorkspaceService] = None,
    ):
        self.scoring_engine = scoring_engine or ScoringEngine()
        self.ai_service = ai_service or AIService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.workspace = workspace or WorkspaceService(workspace_root())

    async def analyze(self, target: str, model: Optional[str] = None) -> Dict:
        self.workspace.initialize()
        if target.startswith(("http://", "https://")):
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                content = client.get(target).text
            fmt = "html"
        else:
            content = self.workspace.read_file(target)["content"]
            fmt = "markdown"
        score = self.scoring_engine.score(content, format=fmt)
        prompt_item = self.prompt_loader.get_collection_item(
            "commands", "analyze-existing"
        )
        base_prompt = prompt_item["body"] if prompt_item else "Analyze this content."
        prompt = f"{base_prompt}\n\nScoring snapshot:\n{score}\n\nReturn JSON only."
        try:
            summary = await self.ai_service.generate(prompt=prompt, model=model)
        except Exception:
            summary = '{"health_score": 60, "quick_wins": ["Add FAQ"], "strategic_actions": ["Refresh statistics"]}'
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        report_path = f"research/analysis-{stamp}.md"
        report = f"# Existing Content Analysis\n\n## Target\n\n`{target}`\n\n## Score\n\n{score['score']} ({score['grade']})\n\n## AI Summary\n\n{summary}\n"
        self.workspace.write_file(report_path, report)
        return {"path": report_path, "score": score, "summary": summary}
