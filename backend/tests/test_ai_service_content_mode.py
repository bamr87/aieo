"""AIService content_mode prompt wiring (no API calls)."""

import pytest

from app.services.ai_service import AIService


def test_build_optimization_prompt_expand_includes_content():
    ai = AIService(openai_api_key="sk-test-not-used")
    body = "# Quickstart\n\nDo the thing."
    prompt = ai._build_optimization_prompt(body, [], "preserve", "expand")
    assert "Quickstart" in prompt
    assert body in prompt


def test_build_optimization_prompt_enhance_lists_gaps():
    ai = AIService(openai_api_key="sk-test-not-used")
    gaps = [{"description": "Add a FAQ section"}]
    prompt = ai._build_optimization_prompt("# X\n", gaps, "preserve", "enhance")
    assert "FAQ" in prompt
    assert "Gaps to fix" in prompt


def test_select_provider_falls_back_to_configured_client():
    # Only Anthropic configured, but the default model name points at OpenAI:
    # generate()/optimize_content() must still route to the configured client.
    ai = AIService(openai_api_key="", anthropic_api_key="sk-ant-test")
    assert ai._select_provider("gpt-5.4") == "anthropic"

    # Only OpenAI configured, but a Claude model requested.
    ai2 = AIService(openai_api_key="sk-test", anthropic_api_key="")
    assert ai2._select_provider("claude-sonnet-4") == "openai"

    # Both configured: prefer the client matching the model name.
    ai3 = AIService(openai_api_key="sk-test", anthropic_api_key="sk-ant-test")
    assert ai3._select_provider("claude-x") == "anthropic"
    assert ai3._select_provider("gpt-4o") == "openai"


def test_select_provider_raises_when_unconfigured():
    ai = AIService(openai_api_key="", anthropic_api_key="")
    with pytest.raises(ValueError):
        ai._select_provider("gpt-4o")
