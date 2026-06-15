"""Use the Claude Code CLI (`claude`) as an AIEO provider via OAuth.

This lets AIEO score and optimize content with the locally authenticated
Claude Code CLI instead of an ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY``. The
CLI manages its own OAuth credentials, so no key needs to live in AIEO config.

The provider is selected with ``provider="claude-cli"`` (aliases:
``claude_cli``, ``claude-code``, ``cli``, ``oauth``) or by setting
``AIEO_PROVIDER=claude-cli`` in the environment.

Environment overrides:
- ``AIEO_CLAUDE_CLI_BIN``     path/name of the CLI binary (default ``claude``)
- ``AIEO_CLAUDE_CLI_MODEL``   model alias passed to ``--model`` (default ``sonnet``)
- ``AIEO_CLAUDE_CLI_TIMEOUT`` per-call timeout in seconds (default ``180``)

The call shells out non-interactively::

    claude -p --output-format json --model <model> [--system-prompt <sys>]

with the user prompt on stdin, and returns the model's text from the JSON
result envelope. Any failure (missing binary, non-zero exit, auth/401, bad
JSON, timeout) raises :class:`ClaudeCLIError`; callers are expected to catch it
and fall back (the scoring engine falls back to heuristic scoring).

Note: vision/screenshot input is not supported through the CLI provider.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Optional

DEFAULT_MODEL = "sonnet"
DEFAULT_TIMEOUT = 180


class ClaudeCLIError(RuntimeError):
    """Raised when the Claude Code CLI invocation fails."""


def _binary() -> str:
    return os.environ.get("AIEO_CLAUDE_CLI_BIN", "claude")


def cli_available(binary: Optional[str] = None) -> bool:
    """Return True if the Claude CLI binary appears to be present and runnable."""
    binary = binary or _binary()
    if os.path.isabs(binary):
        return os.path.isfile(binary) and os.access(binary, os.X_OK)
    return shutil.which(binary) is not None


def _resolve_model(model: Optional[str]) -> str:
    return model or os.environ.get("AIEO_CLAUDE_CLI_MODEL") or DEFAULT_MODEL


def _resolve_timeout(timeout: Optional[int]) -> int:
    if timeout is not None:
        return timeout
    try:
        return int(os.environ.get("AIEO_CLAUDE_CLI_TIMEOUT", str(DEFAULT_TIMEOUT)))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def run_claude_cli(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """Run a single non-interactive completion through the Claude Code CLI.

    Args:
        prompt: The user prompt, sent on stdin.
        system_prompt: Optional system prompt (fully replaces the CLI default).
        model: Model alias for ``--model`` (defaults to ``sonnet`` / env).
        timeout: Per-call timeout in seconds (defaults to env / 180).

    Returns:
        The assistant's text response (the ``result`` field of the JSON envelope).

    Raises:
        ClaudeCLIError: on missing binary, non-zero exit, auth/API error,
            empty/invalid output, or timeout.
    """
    binary = _binary()
    if not cli_available(binary):
        raise ClaudeCLIError(
            f"Claude CLI '{binary}' not found on PATH. Install Claude Code "
            "(https://claude.com/claude-code) or set AIEO_CLAUDE_CLI_BIN."
        )

    model = _resolve_model(model)
    timeout = _resolve_timeout(timeout)

    cmd = [binary, "-p", "--output-format", "json", "--model", model]
    if system_prompt:
        cmd += ["--system-prompt", system_prompt]

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:  # binary vanished between check and exec
        raise ClaudeCLIError(f"Claude CLI '{binary}' not found: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ClaudeCLIError(
            f"Claude CLI timed out after {timeout}s (set AIEO_CLAUDE_CLI_TIMEOUT to raise)"
        ) from exc

    # The CLI writes its JSON envelope to stdout even for API/auth errors (and
    # may still exit non-zero). Prefer the structured message when present, so
    # callers see e.g. "Claude CLI error (HTTP 401): Failed to authenticate"
    # rather than a raw JSON dump.
    stdout = (proc.stdout or "").strip()
    if stdout:
        return _extract_text(stdout)

    if proc.returncode != 0:
        detail = (proc.stderr or "").strip()
        raise ClaudeCLIError(
            f"Claude CLI exited with code {proc.returncode}: {detail[:400] or '(no output)'}"
        )

    raise ClaudeCLIError("Claude CLI returned empty output")


def _extract_text(stdout: str) -> str:
    """Pull the assistant text out of the CLI's ``--output-format json`` envelope."""
    out = (stdout or "").strip()
    if not out:
        raise ClaudeCLIError("Claude CLI returned empty output")

    try:
        envelope = json.loads(out)
    except json.JSONDecodeError:
        # Fall back to treating stdout as raw text (e.g. --output-format text).
        return out

    if not isinstance(envelope, dict):
        return out

    if envelope.get("is_error") or envelope.get("subtype") not in (None, "success"):
        detail = envelope.get("result") or envelope.get("subtype") or "unknown error"
        status = envelope.get("api_error_status")
        suffix = f" (HTTP {status})" if status else ""
        raise ClaudeCLIError(f"Claude CLI error{suffix}: {detail}")

    result = envelope.get("result")
    if not result:
        raise ClaudeCLIError("Claude CLI response did not include a 'result' field")
    return result
