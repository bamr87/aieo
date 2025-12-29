"""AI service for content optimization."""
from typing import Dict, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from ..core.config import settings


class AIService:
    """Service for AI-powered content optimization."""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
    
    async def optimize_content(
        self,
        content: str,
        gaps: list[Dict],
        style: str = "preserve",
        model: Optional[str] = None,
    ) -> str:
        """
        Optimize content using AI to fix gaps.
        
        Args:
            content: Original content
            gaps: List of gaps to fix
            style: 'preserve' or 'aggressive'
            model: Model to use ('gpt-4', 'claude', etc.)
        
        Returns:
            Optimized content
        """
        if not model:
            model = settings.DEFAULT_AI_MODEL
        
        # Build prompt
        prompt = self._build_optimization_prompt(content, gaps, style)
        
        # Call appropriate AI service
        if "claude" in model.lower() and self.anthropic_client:
            return await self._optimize_with_claude(prompt)
        else:
            return await self._optimize_with_openai(prompt, model)
    
    def _build_optimization_prompt(self, content: str, gaps: list[Dict], style: str) -> str:
        """Build optimization prompt."""
        gap_descriptions = "\n".join([f"- {gap['description']}" for gap in gaps[:5]])
        
        style_instruction = (
            "Preserve the original writing style and tone."
            if style == "preserve"
            else "You may modify the writing style to maximize AIEO score."
        )
        
        prompt = f"""You are an AIEO (AI Engine Optimization) expert. Optimize the following content to improve its citation likelihood by AI engines.

Gaps to fix:
{gap_descriptions}

{style_instruction}

Apply these AIEO patterns:
1. Add structured data (tables, lists) where appropriate
2. Increase entity density (people, places, products, dates)
3. Add citation hooks ("According to...", "Research shows...")
4. Add recursive depth (answer follow-up questions)
5. Add temporal anchors (dates, versions)
6. Add comparison tables if comparing items
7. Add explicit definitions
8. Add step-by-step procedures if applicable
9. Add FAQ sections
10. Add meta-context explanations

Original content:
{content}

Return the optimized content:"""
        
        return prompt
    
    async def _optimize_with_openai(self, prompt: str, model: str) -> str:
        """Optimize content using OpenAI."""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=model if model.startswith("gpt") else "gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert content optimizer specializing in AIEO."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise ValueError(f"OpenAI API error: {e}")
    
    async def _optimize_with_claude(self, prompt: str) -> str:
        """Optimize content using Claude."""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")
        
        try:
            message = await self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
            return message.content[0].text
        except Exception as e:
            raise ValueError(f"Anthropic API error: {e}")

