"""Tests for the Claude Code CLI (OAuth) provider integration.

These tests mock the `claude` subprocess so they never make a live call —
they verify command construction, envelope parsing, provider normalization,
the AI->heuristic fallback, and AIService routing.
"""

import json
from types import SimpleNamespace

import pytest

from app.services import claude_cli
from app.services.claude_cli import ClaudeCLIError, _extract_text, run_claude_cli
from app.services.ai_service import AIService
from app.services.optimize_service import OptimizeService
from app.services.scoring_engine import ScoringEngine
from app.services.prompt_loader import PromptLoader


def _success_envelope(text: str) -> str:
    return json.dumps(
        {"type": "result", "subtype": "success", "is_error": False, "result": text}
    )


def _error_envelope(status: int, message: str) -> str:
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": True,
            "api_error_status": status,
            "result": message,
        }
    )


# --------------------------------------------------------------------------
# Envelope parsing
# --------------------------------------------------------------------------


def test_extract_text_success():
    assert _extract_text(_success_envelope("hello world")) == "hello world"


def test_extract_text_raw_text_fallback():
    # Non-JSON stdout (e.g. --output-format text) is returned verbatim.
    assert _extract_text("just plain text") == "just plain text"


def test_extract_text_auth_error_raises_clean_message():
    with pytest.raises(ClaudeCLIError) as exc:
        _extract_text(_error_envelope(401, "Failed to authenticate"))
    assert "401" in str(exc.value)
    assert "Failed to authenticate" in str(exc.value)


def test_extract_text_empty_raises():
    with pytest.raises(ClaudeCLIError):
        _extract_text("")


# --------------------------------------------------------------------------
# run_claude_cli command construction
# --------------------------------------------------------------------------


def test_run_claude_cli_builds_command_and_returns_text(monkeypatch):
    captured = {}

    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None):
        captured["cmd"] = cmd
        captured["input"] = input
        return SimpleNamespace(
            returncode=0, stdout=_success_envelope("scored!"), stderr=""
        )

    monkeypatch.setattr(claude_cli, "cli_available", lambda binary=None: True)
    monkeypatch.setattr(claude_cli.subprocess, "run", fake_run)

    out = run_claude_cli("user prompt here", system_prompt="be terse", model="sonnet")

    assert out == "scored!"
    assert captured["input"] == "user prompt here"
    assert captured["cmd"][0:2] == ["claude", "-p"]
    assert "--output-format" in captured["cmd"] and "json" in captured["cmd"]
    assert "--model" in captured["cmd"] and "sonnet" in captured["cmd"]
    assert "--system-prompt" in captured["cmd"] and "be terse" in captured["cmd"]


def test_run_claude_cli_missing_binary_raises(monkeypatch):
    monkeypatch.setattr(claude_cli, "cli_available", lambda binary=None: False)
    with pytest.raises(ClaudeCLIError):
        run_claude_cli("prompt")


def test_run_claude_cli_surfaces_envelope_error_on_nonzero_exit(monkeypatch):
    # The CLI prints its JSON envelope on stdout even when it exits non-zero.
    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None):
        return SimpleNamespace(
            returncode=1, stdout=_error_envelope(401, "Invalid auth"), stderr=""
        )

    monkeypatch.setattr(claude_cli, "cli_available", lambda binary=None: True)
    monkeypatch.setattr(claude_cli.subprocess, "run", fake_run)

    with pytest.raises(ClaudeCLIError) as exc:
        run_claude_cli("prompt")
    assert "401" in str(exc.value)


# --------------------------------------------------------------------------
# ScoringEngine provider wiring
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alias", ["claude-cli", "claude_cli", "claude-code", "CLI", "oauth"]
)
def test_engine_normalizes_provider_aliases(alias):
    engine = ScoringEngine(provider=alias)
    assert engine.provider == "claude_cli"
    assert engine.model == "sonnet"  # default
    assert engine.api_key is None  # OAuth: no key required


def test_engine_env_opt_in(monkeypatch):
    monkeypatch.setenv("AIEO_PROVIDER", "claude-cli")
    engine = ScoringEngine()
    assert engine.provider == "claude_cli"


def _fake_ai_scoring_json() -> str:
    """Build a minimal-but-valid scoring-rubric JSON for every known pattern."""
    patterns = PromptLoader().load_patterns()
    return json.dumps(
        {
            "content_type": "article",
            "patterns": {
                p["name"]: {
                    "score": p["max_score"],
                    "detected": True,
                    "evidence": ["ok"],
                    "recommendation": "",
                }
                for p in patterns
            },
            "anti_patterns": {"penalties": 0, "detected": [], "evidence": []},
            "overall_assessment": "great",
        }
    )


def test_engine_uses_cli_for_ai_scoring(monkeypatch):
    # The engine imports run_claude_cli lazily from app.services.claude_cli.
    monkeypatch.setattr(
        "app.services.claude_cli.run_claude_cli",
        lambda *a, **k: _fake_ai_scoring_json(),
    )
    engine = ScoringEngine(provider="claude-cli")
    result = engine.score("# Title\n\nSome content.", format="markdown")
    assert result["scoring_method"] == "ai"
    assert result["provider"] == "claude_cli"
    assert result["score"] > 0


def test_engine_falls_back_to_heuristic_on_cli_error(monkeypatch):
    def boom(*a, **k):
        raise ClaudeCLIError("Claude CLI error (HTTP 401): Failed to authenticate")

    monkeypatch.setattr("app.services.claude_cli.run_claude_cli", boom)
    engine = ScoringEngine(provider="claude-cli")
    result = engine.score("# Title\n\nSome content.", format="markdown")
    assert result["scoring_method"] == "heuristic"
    assert 0 <= result["score"] <= 100


# --------------------------------------------------------------------------
# AIService / OptimizeService routing
# --------------------------------------------------------------------------


def test_ai_service_selects_cli_provider():
    svc = AIService(use_claude_cli=True, model="sonnet")
    assert svc._select_provider("gpt-4o") == "claude_cli"
    assert svc._select_provider("claude-3") == "claude_cli"


def test_optimize_service_for_provider_builds_cli_backed_service():
    opt = OptimizeService.for_provider(provider="claude-cli")
    assert opt.scoring_engine.provider == "claude_cli"
    assert opt.ai_service.use_claude_cli is True
    assert opt.ai_service.openai_client is None
    assert opt.ai_service.anthropic_client is None
