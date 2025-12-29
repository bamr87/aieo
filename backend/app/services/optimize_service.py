"""Optimization service for applying AIEO patterns."""

from typing import Dict, List
from .scoring_engine import ScoringEngine
from .ai_service import AIService
from ..core.validation import validate_content_size, sanitize_content


class OptimizeService:
    """Service for optimizing content."""

    def __init__(self):
        self.scoring_engine = ScoringEngine()
        self.ai_service = AIService()

    async def optimize(
        self,
        content: str,
        target_engines: List[str] = None,
        style: str = "preserve",
    ) -> Dict:
        """
        Optimize content with AIEO patterns.

        Args:
            content: Original content
            target_engines: Target AI engines (optional)
            style: 'preserve' or 'aggressive'

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
