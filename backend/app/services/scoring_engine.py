"""AI-orchestrated scoring engine for AIEO patterns.

This engine uses prompt engineering as its core — all scoring criteria,
pattern definitions, and evaluation instructions live in external prompt
files (backend/prompts/). The AI model reads these prompts at runtime and
evaluates content contextually, replacing hardcoded regex pattern matching.

Supports:
- OpenAI (GPT-4, GPT-4o, etc.)
- Anthropic (Claude 3.5, Claude 3, etc.)
- Claude Code CLI via OAuth (provider="claude-cli", no API key needed)
- Heuristic fallback when no provider is configured
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from .content_parser import ContentParser
from .prompt_loader import PromptLoader
from ..analyzers import (
    ContentLengthComparator,
    ContentScorer,
    CROChecker,
    KeywordAnalyzer,
    LandingPageScorer,
    ReadabilityScorer,
    SearchIntentAnalyzer,
    SEOQualityRater,
)

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Score content against AIEO patterns using AI-driven evaluation.

    The scoring criteria are defined entirely in prompt files under
    backend/prompts/. To change scoring behavior, edit the prompts —
    not this code.
    """

    def __init__(
        self,
        prompts_dir: Optional[Path] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.parser = ContentParser()
        self.prompt_loader = PromptLoader(prompts_dir)
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self._resolve_config()
        self.readability_scorer = ReadabilityScorer()
        self.keyword_analyzer = KeywordAnalyzer()
        self.intent_analyzer = SearchIntentAnalyzer()
        self.length_comparator = ContentLengthComparator()
        self.seo_rater = SEOQualityRater()
        self.content_scorer = ContentScorer()
        self.landing_scorer = LandingPageScorer()
        self.cro_checker = CROChecker()

    def _resolve_config(self):
        """Resolve provider/key/model from environment if not explicitly set."""
        # Opt into the Claude Code CLI (OAuth) provider via env when nothing
        # else was passed in, e.g. AIEO_PROVIDER=claude-cli.
        if not self.provider and not self.api_key:
            env_provider = os.environ.get("AIEO_PROVIDER")
            if env_provider:
                self.provider = env_provider

        if self.provider:
            self.provider = self._normalize_provider(self.provider)

        # Explicitly forced heuristic (offline) scoring — never call AI even if
        # the server has a provider key configured.
        if self.provider == "heuristic":
            self.provider = None
            self.api_key = None
            return

        # The Claude Code CLI authenticates over OAuth through the `claude`
        # binary, so it needs no API key. Resolve only the model and return.
        if self.provider == "claude_cli":
            self.model = (
                self.model or os.environ.get("AIEO_CLAUDE_CLI_MODEL") or "sonnet"
            )
            return

        if self.api_key:
            if not self.provider:
                self.provider = self._detect_provider(self.api_key)
            return

        # Try loading from the app's config module
        try:
            from ..core.config import settings

            if settings.OPENAI_API_KEY:
                self.api_key = settings.OPENAI_API_KEY
                self.provider = self.provider or "openai"
                self.model = self.model or settings.DEFAULT_AI_MODEL
            elif settings.ANTHROPIC_API_KEY:
                self.api_key = settings.ANTHROPIC_API_KEY
                self.provider = self.provider or "anthropic"
                self.model = self.model or "claude-sonnet-4-20250514"
        except (ImportError, Exception):
            pass  # Running standalone without full backend config

        # Try environment variables directly
        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get(
                "ANTHROPIC_API_KEY"
            )
            if self.api_key:
                if os.environ.get("OPENAI_API_KEY"):
                    self.provider = self.provider or "openai"
                    self.model = self.model or "gpt-5.4"
                else:
                    self.provider = self.provider or "anthropic"
                    self.model = self.model or "claude-sonnet-4-20250514"

    @staticmethod
    def _detect_provider(api_key: str) -> str:
        """Detect provider from API key format."""
        if api_key.startswith("sk-ant-"):
            return "anthropic"
        return "openai"

    @staticmethod
    def _normalize_provider(provider: str) -> str:
        """Normalize provider aliases to a canonical name.

        The Claude Code CLI (OAuth) provider accepts several friendly spellings;
        they all canonicalize to ``claude_cli``.
        """
        canonical = provider.strip().lower().replace("-", "_")
        if canonical in {
            "claude_cli",
            "claude_code",
            "claude_code_cli",
            "claudecli",
            "cli",
            "oauth",
            "claude_oauth",
        }:
            return "claude_cli"
        if canonical in {"heuristic", "none", "off", "offline"}:
            return "heuristic"
        return canonical

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        content: str,
        format: str = "markdown",
        screenshot_b64: Optional[str] = None,
    ) -> Dict:
        """Score content and return comprehensive results.

        If an AI API key is configured, uses the AI model to evaluate
        content contextually against prompt-defined patterns.
        Otherwise, falls back to lightweight heuristic scoring.

        Args:
            content: Raw content (HTML or markdown).
            format: Content format ('markdown' or 'html').
            screenshot_b64: Optional base64-encoded PNG screenshot for visual analysis.

        Returns:
            Dictionary with score, grade, pattern_scores, gaps,
            anti_pattern_penalties, word_count, visual_analysis
        """
        parsed = self.parser.parse(content, format)

        # The Claude Code CLI provider authenticates via OAuth and needs no key;
        # every other AI provider requires an API key.
        ai_ready = self.provider == "claude_cli" or bool(self.api_key and self.provider)

        if ai_ready:
            try:
                return self._score_with_ai(parsed, screenshot_b64=screenshot_b64)
            except Exception as e:
                logger.warning("AI scoring failed, falling back to heuristic: %s", e)
                return self._score_heuristic(parsed)
        else:
            return self._score_heuristic(parsed)

    # ------------------------------------------------------------------
    # AI-driven scoring
    # ------------------------------------------------------------------

    def _score_with_ai(
        self, parsed: Dict, screenshot_b64: Optional[str] = None
    ) -> Dict:
        """Score content using an AI model with prompt-defined criteria."""
        system_prompt = self.prompt_loader.load_system_prompt()
        user_prompt = self.prompt_loader.build_evaluation_prompt(parsed)

        if screenshot_b64:
            user_prompt += "\n\n## Screenshot\n\nA screenshot of the live page is attached. Use it to evaluate visual layout, design quality, information hierarchy, readability, and UX signals that affect AI citability. Include a `visual_analysis` section in your response."

        raw_response = self._call_ai(
            system_prompt, user_prompt, screenshot_b64=screenshot_b64
        )
        ai_result = self._parse_ai_response(raw_response)

        return self._build_result(ai_result, parsed)

    def _call_ai(
        self, system_prompt: str, user_prompt: str, screenshot_b64: Optional[str] = None
    ) -> str:
        """Call the AI model and return the raw response text."""
        if self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt, screenshot_b64)
        elif self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt, screenshot_b64)
        elif self.provider == "claude_cli":
            return self._call_claude_cli(system_prompt, user_prompt, screenshot_b64)
        else:
            raise ValueError(f"Unknown AI provider: {self.provider}")

    def _call_openai(
        self, system_prompt: str, user_prompt: str, screenshot_b64: Optional[str] = None
    ) -> str:
        """Call OpenAI API (sync), with optional vision input."""
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

        # Build user message content — text + optional image
        user_content: list = [{"type": "text", "text": user_prompt}]
        if screenshot_b64:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_b64}",
                        "detail": "high",
                    },
                }
            )

        response = client.chat.completions.create(
            model=self.model or "gpt-5.4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_completion_tokens=8192,
        )
        return response.choices[0].message.content

    def _call_anthropic(
        self, system_prompt: str, user_prompt: str, screenshot_b64: Optional[str] = None
    ) -> str:
        """Call Anthropic API (sync), with optional vision input."""
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)

        # Build user message content — text + optional image
        user_content: list = [{"type": "text", "text": user_prompt}]
        if screenshot_b64:
            user_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_b64,
                    },
                }
            )

        message = client.messages.create(
            model=self.model or "claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_content},
            ],
        )
        return message.content[0].text

    def _call_claude_cli(
        self, system_prompt: str, user_prompt: str, screenshot_b64: Optional[str] = None
    ) -> str:
        """Call the locally authenticated Claude Code CLI (OAuth, no API key).

        Vision input is not supported through the CLI, so a screenshot — if
        provided — is ignored and the content is scored as text.
        """
        from .claude_cli import run_claude_cli

        if screenshot_b64:
            logger.info(
                "Claude CLI provider does not support screenshot vision; scoring text only."
            )
        return run_claude_cli(
            user_prompt, system_prompt=system_prompt, model=self.model
        )

    def _parse_ai_response(self, raw: str) -> Dict:
        """Parse the AI's JSON response, handling common formatting issues."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI JSON: %s\nRaw: %s", e, raw[:500])
            json_match = re.search(r"\{[\s\S]*\}", cleaned)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"AI returned invalid JSON: {e}")

    def _build_result(self, ai_result: Dict, parsed: Dict) -> Dict:
        """Build the standardized scoring result from AI output."""
        patterns = self.prompt_loader.load_patterns()
        pattern_weights = {p["name"]: p["weight"] for p in patterns}
        pattern_maxes = {p["name"]: p["max_score"] for p in patterns}
        expected_names = {p["name"] for p in patterns}

        ai_patterns = ai_result.get("patterns", {})
        pattern_scores = {}

        for name in expected_names:
            ai_data = ai_patterns.get(name, {})
            max_score = pattern_maxes.get(name, 10)
            raw_score = ai_data.get("score", 0)
            clamped = max(0, min(max_score, raw_score))
            pattern_scores[name] = {
                "score": clamped,
                "max": max_score,
                "detected": ai_data.get("detected", False),
                "evidence": ai_data.get("evidence", []),
                "recommendation": ai_data.get("recommendation", ""),
            }

        # Weighted score normalized to 100
        total_weight = sum(pattern_weights.values())
        weighted_sum = 0.0
        for name, data in pattern_scores.items():
            w = pattern_weights.get(name, 0)
            m = data["max"]
            if m > 0:
                weighted_sum += (data["score"] / m) * w
        normalized = (
            round((weighted_sum / total_weight) * 100, 1) if total_weight > 0 else 0
        )

        anti = ai_result.get("anti_patterns", {})
        anti_penalty = min(50, anti.get("penalties", 0))
        final_score = max(0, normalized - anti_penalty)
        grade = self._score_to_grade(final_score)

        gaps = self._build_gaps(pattern_scores, pattern_weights)

        enriched = self._compute_extra_dimensions(parsed)
        enriched["dimensions"]["aieo"] = final_score
        return {
            "score": final_score,
            "grade": grade,
            "pattern_scores": pattern_scores,
            "gaps": gaps,
            "anti_pattern_penalties": anti_penalty,
            "anti_pattern_details": {
                "detected": anti.get("detected", []),
                "evidence": anti.get("evidence", []),
            },
            "content_type": ai_result.get("content_type", "unknown"),
            "overall_assessment": ai_result.get("overall_assessment", ""),
            "executive_summary": ai_result.get("executive_summary", ""),
            "priority_actions": ai_result.get("priority_actions", []),
            "sample_improvements": ai_result.get("sample_improvements", []),
            "visual_analysis": ai_result.get("visual_analysis", {}),
            "word_count": parsed["word_count"],
            "scoring_method": "ai",
            "model": self.model,
            "provider": self.provider,
            **enriched,
        }

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _build_gaps(self, pattern_scores: Dict, pattern_weights: Dict) -> List[Dict]:
        """Generate gap analysis from pattern scores."""
        gaps = []
        for name, data in pattern_scores.items():
            max_s = data["max"]
            if max_s == 0:
                continue
            ratio = data["score"] / max_s
            weight = pattern_weights.get(name, 0)

            if ratio < 0.6:
                if ratio < 0.3:
                    severity = "high" if weight >= 15 else "medium"
                else:
                    severity = "medium" if weight >= 15 else "low"

                recommendation = data.get("recommendation", "")
                if not recommendation:
                    recommendation = (
                        f"Improve {name.replace('_', ' ')} to increase score."
                    )

                gaps.append(
                    {
                        "id": f"gap_{name}",
                        "category": name,
                        "severity": severity,
                        "description": recommendation,
                        "pattern_score": data["score"],
                        "pattern_max": max_s,
                        "weight": weight,
                    }
                )

        severity_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: (severity_order.get(g["severity"], 3), -g["weight"]))
        return gaps

    @staticmethod
    def _score_to_grade(score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    # ------------------------------------------------------------------
    # Heuristic fallback (no API key)
    # ------------------------------------------------------------------

    def _score_heuristic(self, parsed: Dict) -> Dict:
        """Lightweight heuristic scoring when no AI API key is available.

        Provides a structural baseline — edit the prompt files and configure
        an AI API key for full contextual scoring.
        """
        patterns = self.prompt_loader.load_patterns()
        pattern_weights = {p["name"]: p["weight"] for p in patterns}

        pattern_scores = {}
        for p in patterns:
            name = p["name"]
            scorer = _HEURISTIC_SCORERS.get(name)
            if scorer:
                pattern_scores[name] = scorer(parsed, p["max_score"])
            else:
                pattern_scores[name] = {
                    "score": 0,
                    "max": p["max_score"],
                    "detected": False,
                    "evidence": [],
                    "recommendation": f"Configure AI API key for {name} scoring.",
                }

        total_weight = sum(pattern_weights.values())
        weighted_sum = 0.0
        for name, data in pattern_scores.items():
            w = pattern_weights.get(name, 0)
            m = data["max"]
            if m > 0:
                weighted_sum += (data["score"] / m) * w
        normalized = (
            round((weighted_sum / total_weight) * 100, 1) if total_weight > 0 else 0
        )

        anti_penalty = _heuristic_anti_patterns(parsed)
        final_score = max(0, normalized - anti_penalty)
        grade = self._score_to_grade(final_score)
        gaps = self._build_gaps(pattern_scores, pattern_weights)

        enriched = self._compute_extra_dimensions(parsed)
        enriched["dimensions"]["aieo"] = final_score
        return {
            "score": final_score,
            "grade": grade,
            "pattern_scores": pattern_scores,
            "gaps": gaps,
            "anti_pattern_penalties": anti_penalty,
            "anti_pattern_details": {"detected": [], "evidence": []},
            "content_type": "unknown",
            "overall_assessment": "Scored with heuristic fallback. Configure an AI API key for contextual analysis.",
            "word_count": parsed["word_count"],
            "scoring_method": "heuristic",
            "model": None,
            "provider": None,
            **enriched,
        }

    def _compute_extra_dimensions(self, parsed: Dict) -> Dict:
        """Compute additional SEO and content quality dimensions."""
        text = parsed.get("text", "")
        readability = self.readability_scorer.score(text)
        keyword_analysis = self.keyword_analyzer.analyze(text)
        search_intent = self.intent_analyzer.analyze(text)
        serp_comparison = self.length_comparator.compare(text)
        seo_quality = self.seo_rater.rate(text)
        humanity = self.content_scorer.score(text)
        cro = {
            "landing_page": self.landing_scorer.score(text),
            "checklist": self.cro_checker.check(text),
        }
        dimensions = {
            "aieo": None,  # populated by caller using main score
            "seo": seo_quality.get("score", 0),
            "readability": readability.get("score", 0),
            "humanity": humanity.get("humanity", 0),
            "cro": cro["landing_page"].get("score", 0),
        }
        return {
            "seo_quality": seo_quality,
            "readability": readability,
            "search_intent": search_intent,
            "keyword_analysis": keyword_analysis,
            "serp_comparison": serp_comparison,
            "humanity": humanity,
            "cro": cro,
            "dimensions": dimensions,
        }


# ======================================================================
# Heuristic scorer functions (module-level, stateless)
# ======================================================================


def _h_structured_data(parsed: Dict, max_score: int) -> Dict:
    wc = parsed["word_count"] or 1
    t, li, h = len(parsed["tables"]), len(parsed["lists"]), len(parsed["headers"])
    density = ((t + li + h) / wc) * 500
    score = min(max_score, (density / 2) * max_score)
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": density >= 1,
        "evidence": [f"{t} tables, {li} lists, {h} headers"],
        "recommendation": "Add tables or lists to organize your content.",
    }


def _h_entity_density(parsed: Dict, max_score: int) -> Dict:
    text, wc = parsed["text"], parsed["word_count"] or 1
    caps = set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text))
    acros = set(re.findall(r"\b[A-Z]{2,6}\b", text))
    stops = {
        "THE",
        "AND",
        "FOR",
        "BUT",
        "NOT",
        "YOU",
        "ALL",
        "CAN",
        "HER",
        "WAS",
        "ONE",
        "OUR",
        "OUT",
        "ARE",
        "HAS",
        "HIS",
        "HOW",
        "ITS",
        "FROM",
        "WITH",
        "THIS",
        "THAT",
        "HAVE",
        "WILL",
        "WHAT",
        "WHEN",
    }
    ents = {e for e in (caps | acros) if e.upper() not in stops and len(e) > 1}
    per100 = (len(ents) / wc) * 100
    score = min(max_score, (per100 / 3) * max_score)
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": per100 >= 1,
        "evidence": [f"{len(ents)} entities ({round(per100, 1)} per 100 words)"],
        "recommendation": "Add specific names, organizations, and product references.",
    }


def _h_citation_hooks(parsed: Dict, max_score: int) -> Dict:
    text = parsed["text"].lower()
    pats = [
        r"according to\b",
        r"research (?:from|by)\b",
        r"study (?:found|shows)\b",
        r"source:",
        r"references?:",
        r"published (?:by|in)\b",
    ]
    count = sum(len(re.findall(p, text)) for p in pats)
    ext = [
        lnk
        for lnk in parsed.get("links", [])
        if lnk.get("url", "").startswith(("http://", "https://"))
    ]
    count += len(ext)
    wc = parsed["word_count"] or 1
    per1k = (count / wc) * 1000
    score = min(max_score, (per1k / 2) * max_score)
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": count > 0,
        "evidence": [f"{count} citation signals ({len(ext)} external links)"],
        "recommendation": "Add source attributions like 'According to [source]...'",
    }


def _h_recursive_depth(parsed: Dict, max_score: int) -> Dict:
    text = parsed["text"]
    qs = re.findall(r"[^.!?\n]+\?", text)
    qh = [h for h in parsed["headers"] if "?" in h["text"]]
    score = min(max_score, len(qs) * 0.5 + len(qh) * 2.5)
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": len(qs) > 0,
        "evidence": [f"{len(qs)} questions, {len(qh)} question headers"],
        "recommendation": "Add FAQ sections or question-style headers.",
    }


def _h_temporal_anchoring(parsed: Dict, max_score: int) -> Dict:
    text = parsed["text"]
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", text))
    fresh = re.findall(r"(?:as of|updated|version\s+\d)", text, re.IGNORECASE)
    count = len(years) + len(fresh)
    score = min(max_score, count * 2)
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": count > 0,
        "evidence": [f"{len(years)} year references, {len(fresh)} freshness signals"],
        "recommendation": "Add dates, version numbers, or 'as of [date]' markers.",
    }


def _h_comparison_tables(parsed: Dict, max_score: int) -> Dict:
    t = parsed["tables"]
    score = min(max_score, len(t) * 5)
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": len(t) > 0,
        "evidence": [f"{len(t)} tables found"],
        "recommendation": "Add comparison tables for key topics.",
    }


def _h_definitional_precision(parsed: Dict, max_score: int) -> Dict:
    text = parsed["text"]
    defs = re.findall(r"(?:is defined as|refers to|means that)\b", text, re.IGNORECASE)
    score = min(max_score, len(defs) * 3)
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": len(defs) > 0,
        "evidence": [f"{len(defs)} definitional phrases"],
        "recommendation": "Add explicit definitions for key terms.",
    }


def _h_procedural_clarity(parsed: Dict, max_score: int) -> Dict:
    text = parsed["text"]
    steps = re.findall(r"step\s+\d+", text, re.IGNORECASE)
    ordered = [li for li in parsed["lists"] if li["type"] == "ordered"]
    score = min(max_score, len(steps) * 0.5 + len(ordered) * 1)
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": len(steps) > 0 or len(ordered) > 0,
        "evidence": [f"{len(steps)} step refs, {len(ordered)} ordered lists"],
        "recommendation": "Add numbered step-by-step instructions.",
    }


def _h_faq_injection(parsed: Dict, max_score: int) -> Dict:
    text = parsed["text"].lower()
    has_faq = bool(
        re.search(r"(?:frequently asked questions|faq|common questions)", text)
    )
    qh = [h for h in parsed["headers"] if "?" in h["text"]]
    score = min(max_score, (8 if has_faq else 0) + min(4, len(qh)))
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": has_faq or len(qh) > 0,
        "evidence": [
            f"FAQ section: {'yes' if has_faq else 'no'}, {len(qh)} question headers"
        ],
        "recommendation": "Add a FAQ section with common questions.",
    }


def _h_meta_context(parsed: Dict, max_score: int) -> Dict:
    text = parsed["text"].lower()
    pats = [
        r"this (?:is |matters? )(?:important|critical|crucial) because",
        r"significantly",
        r"essential",
    ]
    count = sum(len(re.findall(p, text)) for p in pats)
    score = min(max_score, count * 2)
    return {
        "score": round(score, 1),
        "max": max_score,
        "detected": count > 0,
        "evidence": [f"{count} meta-context signals"],
        "recommendation": "Explain why your content matters to the reader.",
    }


_HEURISTIC_SCORERS = {
    "structured_data": _h_structured_data,
    "entity_density": _h_entity_density,
    "citation_hooks": _h_citation_hooks,
    "recursive_depth": _h_recursive_depth,
    "temporal_anchoring": _h_temporal_anchoring,
    "comparison_tables": _h_comparison_tables,
    "definitional_precision": _h_definitional_precision,
    "procedural_clarity": _h_procedural_clarity,
    "faq_injection": _h_faq_injection,
    "meta_context": _h_meta_context,
}


def _heuristic_anti_patterns(parsed: Dict) -> int:
    """Detect anti-patterns via heuristic checks."""
    penalties = 0
    text = parsed["text"].lower()
    wc = parsed["word_count"]

    if wc > 0:
        density = (
            (len(parsed["tables"]) + len(parsed["lists"]) + len(parsed["headers"]))
            / wc
            * 1000
        )
        if density > 10:
            penalties += 20

    words = text.split()
    if words:
        freq: Dict[str, int] = {}
        for w in words:
            if len(w) > 4:
                freq[w] = freq.get(w, 0) + 1
        for _, c in freq.items():
            if c > len(words) * 0.05:
                penalties += 15
                break

    if wc > 1000 and not parsed["tables"] and not parsed["lists"]:
        penalties += 15

    return penalties
