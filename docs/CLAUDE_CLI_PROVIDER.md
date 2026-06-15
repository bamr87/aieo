# Claude Code CLI provider (OAuth)

AIEO can score and optimize content through the **locally authenticated Claude
Code CLI** instead of an `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`. The `claude`
binary manages its own OAuth credentials, so no API key needs to live in AIEO
config — if `claude` is installed and logged in, AIEO can use it.

This is the `claude-cli` provider. It is accepted anywhere a provider is
accepted (the scoring engine, `OptimizeService`, `tools.aieo_runner`,
`run_audit.py`).

## How it works

`backend/app/services/claude_cli.py` shells out non-interactively:

```
claude -p --output-format json --model <model> [--system-prompt <system>]
```

with the prompt on stdin, and reads the model's text from the JSON `result`
envelope. The same evaluation prompts that drive the OpenAI/Anthropic paths are
sent to the CLI, so scoring output is at parity.

- Selecting it: `provider="claude-cli"` (aliases: `claude_cli`, `claude-code`,
  `cli`, `oauth`) or `AIEO_PROVIDER=claude-cli` in the environment.
- No API key is required.
- Any failure (missing binary, auth/401, timeout, bad JSON) raises
  `ClaudeCLIError`; the **scoring engine catches it and falls back to heuristic
  scoring**, so an audit never hard-fails because the CLI is unavailable.
- **Vision is not supported** through the CLI — screenshots are ignored and
  content is scored as text. Use the `anthropic`/`openai` providers for visual
  analysis.

### Environment overrides

| Variable | Default | Purpose |
| --- | --- | --- |
| `AIEO_CLAUDE_CLI_BIN` | `claude` | Path/name of the CLI binary |
| `AIEO_CLAUDE_CLI_MODEL` | `sonnet` | Model alias passed to `--model` |
| `AIEO_CLAUDE_CLI_TIMEOUT` | `180` | Per-call timeout (seconds) |
| `AIEO_PROVIDER` | _(unset)_ | Set to `claude-cli` to opt in without a flag |

## Validating against a content repo (e.g. zer0-mistakes)

`tools.aieo_runner` discovers local markdown by glob and scores each file — no
backend services, DB, or API key needed.

```bash
# from the aieo repo root
pip install -r backend/requirements-ci.txt

# 1) Heuristic baseline (offline, no AI) — works anywhere
PYTHONPATH=backend python -m tools.aieo_runner \
  --root ~/github/zer0-mistakes --glob 'pages/*.md' --glob 'docs/**/*.md' \
  --mode audit-only --output-dir aieo-artifacts/zer0-heuristic

# 2) AI scoring via Claude Code CLI (OAuth) — run from your own terminal,
#    where `claude` is logged in. No API key required.
PYTHONPATH=backend python -m tools.aieo_runner \
  --root ~/github/zer0-mistakes --glob 'pages/*.md' --glob 'docs/**/*.md' \
  --mode audit-only --provider claude-cli \
  --output-dir aieo-artifacts/zer0-claude-cli

# 3) Score + AI rewrite (enhance) into proposed/, without touching sources
PYTHONPATH=backend python -m tools.aieo_runner \
  --root ~/github/zer0-mistakes --glob 'pages/faq.md' \
  --mode enhance --provider claude-cli --write-proposed \
  --output-dir aieo-artifacts/zer0-rewrite
```

Each run writes `REPORT.md` plus per-file JSON under `results/`. Diff the
heuristic and `claude-cli` reports to see how AI scoring differs from the
offline heuristic.

Batch URL audits accept the provider too:

```bash
python run_audit.py --provider claude-cli   # audits sites.txt via OAuth
```

## Self-test

If a run silently falls back to heuristic, confirm the CLI itself is authed:

```bash
echo 'Reply with only: {"ok": true}' | claude -p --output-format json --model sonnet
```

A `"result"` containing the JSON means OAuth is working. An
`api_error_status: 401` means you need to log in (`claude` once interactively).
Note: a fresh `claude -p` started from *inside* another Claude Code/agent
session can 401 because it doesn't inherit the parent session's in-memory
token — run the validation from a normal terminal.
