"""AI service for content optimization."""

from pathlib import Path
from typing import Dict, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from ..core.config import settings

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


class AIService:
    """Service for AI-powered content optimization."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        use_claude_cli: bool = False,
        model: Optional[str] = None,
    ):
        oa = (
            openai_api_key
            if openai_api_key is not None
            else settings.OPENAI_API_KEY
        )
        an = (
            anthropic_api_key
            if anthropic_api_key is not None
            else settings.ANTHROPIC_API_KEY
        )
        self.openai_client = AsyncOpenAI(api_key=oa) if oa else None
        self.anthropic_client = AsyncAnthropic(api_key=an) if an else None
        # When set, optimize/generate calls route through the locally
        # authenticated Claude Code CLI (OAuth) instead of an API key.
        self.use_claude_cli = use_claude_cli
        self.cli_model = model

    def _load_expand_instructions(self) -> str:
        path = _PROMPTS_DIR / "optimize_expand.md"
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return ""

    def _select_provider(self, model: str) -> str:
        """Pick a configured provider, preferring the one matching the model name.

        Falls back to whichever client is configured when the preferred one is
        not, so an Anthropic-only (or OpenAI-only) setup still works even when the
        default model name points at the other provider.
        """
        if self.use_claude_cli:
            return "claude_cli"
        prefers_claude = "claude" in model.lower()
        if prefers_claude and self.anthropic_client:
            return "anthropic"
        if not prefers_claude and self.openai_client:
            return "openai"
        if self.anthropic_client:
            return "anthropic"
        if self.openai_client:
            return "openai"
        raise ValueError(
            "No AI provider configured (set OPENAI_API_KEY or ANTHROPIC_API_KEY)"
        )

    async def optimize_content(
        self,
        content: str,
        gaps: list[Dict],
        style: str = "preserve",
        model: Optional[str] = None,
        content_mode: str = "enhance",
    ) -> str:
        """
        Optimize content using AI to fix gaps.

        Args:
            content: Original content
            gaps: List of gaps to fix
            style: 'preserve' or 'aggressive'
            model: Model to use ('gpt-4', 'claude', etc.)
            content_mode: 'enhance' (gap-driven edits) or 'expand' (add depth/sections)

        Returns:
            Optimized content
        """
        if not model:
            model = settings.DEFAULT_AI_MODEL

        prompt = self._build_optimization_prompt(content, gaps, style, content_mode)

        provider = self._select_provider(model)
        if provider == "claude_cli":
            return await self._optimize_with_claude_cli(prompt, model)
        if provider == "anthropic":
            return await self._optimize_with_claude(prompt, model)
        return await self._optimize_with_openai(prompt, model)

    async def generate(self, prompt: str, model: Optional[str] = None) -> str:
        """Run a generic prompt completion."""
        chosen_model = model or settings.DEFAULT_AI_MODEL
        provider = self._select_provider(chosen_model)
        if provider == "claude_cli":
            return await self._optimize_with_claude_cli(prompt, chosen_model)
        if provider == "anthropic":
            return await self._optimize_with_claude(prompt, chosen_model)
        return await self._optimize_with_openai(prompt, chosen_model)

    def _build_optimization_prompt(
        self,
        content: str,
        gaps: list[Dict],
        style: str,
        content_mode: str = "enhance",
    ) -> str:
        """Build optimization prompt."""
        if content_mode == "expand":
            instructions = self._load_expand_instructions()
            gap_descriptions = "\n".join(
                [f"- {gap['description']}" for gap in gaps[:10]]
            )
            style_instruction = (
                "Preserve the author's voice where possible while adding structured depth."
                if style == "preserve"
                else "You may substantially reshape sections for clarity and citability."
            )
            return f"""{instructions}

## Scoring gaps to address (where relevant)
{gap_descriptions if gap_descriptions else "- (none listed — still expand for structure and depth)"}

## Tone
{style_instruction}

## Original content
{content}

Return the full expanded markdown document only:"""

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
                model=model if model.startswith("gpt") else "gpt-5.4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content optimizer specializing in AIEO.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise ValueError(f"OpenAI API error: {e}")

    async def _optimize_with_claude_cli(self, prompt: str, model: Optional[str]) -> str:
        """Optimize content using the Claude Code CLI (OAuth, no API key)."""
        import asyncio

        from .claude_cli import run_claude_cli

        # Only forward an explicit Claude model name; otherwise let the CLI
        # helper apply its default (sonnet / AIEO_CLAUDE_CLI_MODEL).
        cli_model = (
            model
            if (model and "claude" in str(model).lower())
            else self.cli_model
        )
        return await asyncio.to_thread(run_claude_cli, prompt, model=cli_model)

    async def _optimize_with_claude(self, prompt: str, model: str) -> str:
        """Optimize content using Claude."""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")

        claude_model = model if "claude" in model.lower() else "claude-3-opus-20240229"
        try:
            message = await self.anthropic_client.messages.create(
                model=claude_model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
            return message.content[0].text
        except Exception as e:
            raise ValueError(f"Anthropic API error: {e}")
