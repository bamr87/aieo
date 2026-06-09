"""Optimization service for applying AIEO patterns."""

from pathlib import Path
from typing import Dict, List, Optional
from .scoring_engine import ScoringEngine
from .ai_service import AIService
from ..core.validation import validate_content_size, sanitize_content


class OptimizeService:
    """Service for optimizing content."""

    def __init__(
        self,
        scoring_engine: Optional[ScoringEngine] = None,
        ai_service: Optional[AIService] = None,
    ):
        self.scoring_engine = scoring_engine or ScoringEngine()
        self.ai_service = ai_service or AIService()

    @classmethod
    def for_provider(
        cls,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompts_dir: Optional[Path] = None,
    ) -> "OptimizeService":
        """Build service with explicit provider/key/model (CLI / CI)."""
        engine = ScoringEngine(
            prompts_dir=prompts_dir,
            provider=provider,
            api_key=api_key,
            model=model,
        )
        openai_key = None
        anthropic_key = None
        if api_key:
            if engine.provider == "anthropic":
                anthropic_key = api_key
            else:
                openai_key = api_key
        ai = AIService(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
        )
        return cls(scoring_engine=engine, ai_service=ai)

    async def optimize(
        self,
        content: str,
        target_engines: List[str] = None,
        style: str = "preserve",
        content_mode: str = "enhance",
        model: Optional[str] = None,
    ) -> Dict:
        """
        Optimize content with AIEO patterns.

        Args:
            content: Original content
            target_engines: Target AI engines (optional)
            style: 'preserve' or 'aggressive'
            content_mode: 'enhance' or 'expand'
            model: Optional model override for the AI optimize call

        Returns:
            Optimization result with optimized content and changes
        """
        # Validate and sanitize input
        content = sanitize_content(content)
        validate_content_size(content)

        # Score original content
        original_score = self.scoring_engine.score(content)
        score_before = original_score["score"]

        # Get gaps
        gaps = original_score.get("gaps", [])

        # Optimize using AI
        optimized_content = await self.ai_service.optimize_content(
            content=content,
            gaps=gaps,
            style=style,
            model=model,
            content_mode=content_mode,
        )

        # Score optimized content
        optimized_score = self.scoring_engine.score(optimized_content)
        score_after = optimized_score["score"]
        uplift = score_after - score_before

        # Generate change list
        changes = self._generate_changes(content, optimized_content, gaps)

        return {
            "optimized_content": optimized_content,
            "score_before": score_before,
            "score_after": score_after,
            "uplift": uplift,
            "changes": changes,
        }

    def _generate_changes(
        self,
        original: str,
        optimized: str,
        gaps: List[Dict],
    ) -> List[Dict]:
        """Generate list of changes made."""
        changes = []

        # Simple diff-based change detection
        # In production, use a proper diff library
        if original != optimized:
            # Estimate changes based on gaps fixed
            for gap in gaps[:10]:  # Limit to top 10 gaps
                changes.append(
                    {
                        "type": "inject",
                        "description": f"Fixed: {gap['description']}",
                        "location": {"start": 0, "end": 0},  # Placeholder
                        "original_text": "",
                        "optimized_text": "",
                        "expected_uplift": 5,  # Estimate
                    }
                )

        return changes
