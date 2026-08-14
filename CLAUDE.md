# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AIEO ("AI Engine Optimization") scores, audits, and optimizes website content for *citability by AI engines* (ChatGPT, Claude, Gemini, Perplexity), and now also runs a full content lifecycle (research → write → rewrite → publish). The codebase is exposed through three surfaces that all share the same `backend/app/services/` layer: a FastAPI REST API, an MCP server, and a CLI / standalone scripts.

## The central design rule: scoring lives in prompts, not code

The most important thing to understand before changing scoring behavior: **all scoring criteria, pattern weights, and evaluation instructions live in markdown files under `backend/prompts/`, not in Python.** To change how content is scored, edit a prompt file — do not add scoring logic to Python.

- `backend/prompts/system.md` — the AI's role and evaluation principles
- `backend/prompts/scoring_rubric.md` — output JSON format, scoring rules, anti-patterns
- `backend/prompts/patterns/*.md` — one file per scoring pattern, each with YAML frontmatter (`name`, `display_name`, `weight`, `max_score`). Dropping a new `.md` file here adds a pattern; no code change.
- `backend/prompts/agents/*.md` — specialized content agents (content-analyzer, seo-optimizer, editor, etc.)
- `backend/prompts/commands/*.md` — lifecycle command prompts (research, write, rewrite, scrub, priorities, analyze-existing)

`PromptLoader` ([backend/app/services/prompt_loader.py](backend/app/services/prompt_loader.py)) reads and caches these files and assembles the evaluation prompt. It parses frontmatter with a simple line-based `key: value` parser (not full YAML) — keep frontmatter flat.

## Scoring flow (two paths)

`ScoringEngine.score()` ([backend/app/services/scoring_engine.py](backend/app/services/scoring_engine.py)) is the heart of audit:

1. `ContentParser` turns HTML/markdown into a structured summary (headers, tables, lists, links, text).
2. **If an API key is configured** (OpenAI or Anthropic), it sends the assembled prompt + parsed content (optionally a base64 screenshot for vision) to the model and parses the returned JSON. `scoring_method: "ai"`.
3. **If no key**, it falls back to module-level heuristic scorer functions (`_HEURISTIC_SCORERS` in the same file) that do regex/structural analysis. `scoring_method: "heuristic"`. AI failures also fall back to heuristic.
4. Either path normalizes weighted pattern scores to 0–100, applies anti-pattern penalties, assigns a letter grade, and calls `_compute_extra_dimensions()` to add the SEO/readability/humanity/CRO dimensions from `backend/app/analyzers/`.

Provider/model/key resolution order (`_resolve_config`): explicit args → `core.config.settings` → `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` env vars. `scoring_engine_legacy.py` is the old hardcoded-rules engine, kept for reference — prefer `scoring_engine.py`.

A third provider, **`claude-cli`** (aliases `claude_cli`/`claude-code`/`cli`/`oauth`, or `AIEO_PROVIDER=claude-cli`), scores via the locally authenticated **Claude Code CLI over OAuth — no API key**. `backend/app/services/claude_cli.py` shells out to `claude -p --output-format json` and is used by both `ScoringEngine` (audit) and `AIService` (optimize/rewrite). It needs no key, ignores screenshots (no vision), and on any failure (missing binary, 401, timeout) raises `ClaudeCLIError` so scoring falls back to heuristic. See [docs/CLAUDE_CLI_PROVIDER.md](docs/CLAUDE_CLI_PROVIDER.md).

## Service-oriented architecture

Each capability is a service class in `backend/app/services/` consumed by all three surfaces. Key ones beyond scoring:

- `AgentRunner` — runs a named prompt agent from `prompts/agents/` against content, auto-injecting workspace `context/*.md` files (brand voice, style guide, keywords) into the prompt. Agents are prompt files, not Python classes.
- `WorkspaceService` — filesystem-backed content workspace rooted at `WORKSPACE_ROOT` (default `.aieo-workspace/`). Creates/manages dirs: `context/`, `topics/`, `research/`, `drafts/`, `rewrites/`, `published/`, `landing-pages/`, `audits/`, etc.
- Lifecycle services: `research_service`, `write_service`, `rewrite_service`, `analyze_existing_service`, `scrub_service`, `priorities_service`, `landing_service`.
- `data_service` + `backend/app/integrations/` — GA4, Google Search Console, DataForSEO connectors (with caching via `integrations/cache.py`).
- `publish_service` + `backend/app/publishers/wordpress_publisher.py` — WordPress publishing.
- `ai_service` — shared async OpenAI/Anthropic wrapper used by lifecycle services and `AgentRunner`.

## The three surfaces (all thin wrappers over services)

- **REST API** — `backend/app/main.py` mounts routers from `backend/app/api/v1/` under `/api/v1`: audit, optimize, citations, patterns, workspace, content. Lifecycle endpoints live in `content.py` under `/api/v1/aieo/*` (e.g. `/api/v1/aieo/research`, `/aieo/write`, `/aieo/publish/wordpress`). Async tasks use Celery (`backend/app/tasks/`).
- **MCP server** — [backend/app/mcp_server.py](backend/app/mcp_server.py) exposes ~20 `aieo_*` tools (`aieo_score_content`, `aieo_audit_url`, `aieo_research`, `aieo_workspace_*`, etc.). Run with `python -m backend.app.mcp_server`. This is what Claude Desktop / Copilot call.
- **CLI & standalone scripts** — `cli/aieo/` is a Click CLI (`audit`, `optimize`, `dashboard`, `crawl`, `context`). Repo-root `run_audit.py` (batch audit of URLs in `sites.txt`), `crawl_site.py` (site snapshot — see below), `build_context.py` (site context — see below), and `generate_reports.py` run *without the full backend* — they import the relevant service directly and work in heuristic/offline mode with no API key.

## Site snapshot (offline site copy)

Separate from scoring: `backend/app/services/site_snapshot/` (package, public class `SiteSnapshotService`) crawls a Jekyll/static site into a cached, offline, multi-format copy for review/analysis/backup. Discovery is Jekyll-tuned (`sitemap.xml` → `feed.xml` → `robots.txt` → same-domain link BFS); every page is cached under `<workspace>/.cache/snapshots/<slug>/` with conditional GET (ETag/Last-Modified) + content hashing, so re-runs only re-fetch changed pages. Exports (text/json/markdown/html/pdf/bundle) all derive from one in-memory model in `model.py`; PDF has a pure-stdlib floor (`pdf_writer.py`, zero new deps) that upgrades to reportlab/Playwright if installed. Exposed on all surfaces: `crawl_site.py`, `aieo crawl`, MCP `aieo_crawl_site`/`aieo_crawl_manifest`, and `POST /api/v1/aieo/snapshot`. The SSRF guard lives in `fetcher.py` (do **not** rely on `core.validation.validate_url`, which does not block private hosts). Tests are fully offline in `backend/tests/test_site_snapshot.py`. See `docs/SNAPSHOT.md`.

## Site context (crawl a URL N levels down into a dataset)

`backend/app/services/site_context/` (package, public class `SiteContextService`) builds a **contextual dataset** for a seed URL and the pages below it — aimed at a *section* (e.g. `/category/programming`), not a whole domain. Three phases, each stoppable: **map** (`link_map.py` — level-ordered BFS from the seed recording nodes/edges/references; depth is measured from the seed, each level has its own budget, scope is `host`/`domain`/`path`), **extract** (`extraction.py` — re-reads the cached bodies with no second request, then `presentation.py` for styles/palette/type/images/animation and `seo.py` for metadata facts + issues), and **analyze** (`agent.py` — loops pages through the **Claude Code CLI over OAuth**, then one site-level synthesis call).

Key points when changing it:

- The agent's instructions are markdown: `prompts/agents/site-context-analyst.md`
(per page) and `site-context-synthesizer.md` (site level). Change what the analysis looks for there, not in Python. Python emits *facts*; judgement is the agent's.
- **Interactive content is content.** `keep_interactive` (default on) preserves
`<form>` subtrees and `hidden` demo containers that the snapshot extractor strips as chrome — a page whose payload is a live demo is otherwise extracted as an empty heading. Same-host JS is fetched and scanned so script-driven motion (rAF/canvas/scripted SVG) is not reported as "static".
- `resources.py` classifies every link before it reaches the frontier: source
downloads (`.py`, `.java`, …), archives, documents, media are typed assets, not crawlable pages.
- Optional upgrades live in `adapters.py` (trafilatura / extruct / protego) and
`renderer.py` (Playwright `--render`), all used only if installed and always falling back — same "stdlib floor, upgrade if present" shape as `pdf_writer`. Extraction is **not** delegated wholesale to trafilatura: it scores ~0.92 F1 on articles but ~0.52 on collections/listings, and context builds are seeded on exactly those, so `--extractor auto` uses it for articles only.
- The agent pass is bounded (`agent_max_pages`, `agent_concurrency`,
`agent_timeout`, and a 3-strike circuit breaker) and **always** degrades to deterministic heuristics — each node records `analysis_method` (`agent`/`heuristic`/`skipped`).
- Unlike the snapshot crawler it must **not** deny `/category/`, `/tag/` or
`/page/` (that is where section seeds and their items live); only real pagination traps are dropped.
- Bodies reuse the snapshot cache (`.cache/snapshots/<site_slug>/`); context
  manifests live beside them in `context/<context_key>.json`.
- Exposed on all surfaces: `build_context.py`, `aieo context`, MCP
`aieo_site_context`/`aieo_context_map`/`aieo_context_manifest`, and `POST /api/v1/aieo/context`. Tests are fully offline (fixture site + a fake `claude` binary) in `backend/tests/test_site_context.py`. See `docs/SITE_CONTEXT.md`.

## Frontend (`frontend/`)

A React 19 + TypeScript + Vite SPA (Tailwind v4) that consumes the same REST API. It's a thin client over `/api/v1/aieo/*` — no business logic. Key conventions for changing it:

- **Design system in `src/components/ui/`** (Button, Card, Field, Badge, ScoreRing, Modal, Tabs, JsonView, Markdown/ContentViewer, …) built on Tailwind tokens in `src/index.css` (`bg-canvas`/`bg-card`/`text-ink`/`text-muted`/`bg-brand`/…). Compose these; don't hand-roll styles. App shell + grouped sidebar nav is `src/components/AppShell.tsx` + `src/components/nav.ts`.
- **API layer in `src/services/`** — typed client (`api.ts`, normalized `ApiError`, request timeouts), one module per area, imported via the `services` barrel. Every call needs an `X-API-Key` (set in the Settings page → localStorage). Audit/optimize accept a `provider` (`auto`/`claude-cli`/`openai`/`anthropic`/`heuristic`) via the provider selector.
- **Hooks** — `useSettings` (key/provider/model), `useToast`, `useAsyncAction` (loading/error; `run(thunk)` returns the value or `undefined`), `useAuditHistory`.
- Pages use loading/error/empty states (never raw `<pre>` JSON dumps — use `JsonView`/`ContentViewer`). Backend `/aieo/agent/run` returns `{agent, result}`; unwrap readable text with `lib/agentText.ts`. The audit endpoint passes the **full** scoring result through (dimensions, pattern_scores, scoring_method), not just score/grade.
- Run: `cd frontend && npm install && npm run dev` (5173). Backend can run headless on sqlite: `AIEO_HEADLESS=1 DATABASE_URL=sqlite:///./aieo_dev.db REDIS_URL= uvicorn app.main:app --port 8000`.

## Commands

```bash
# Backend (run from repo root unless noted)
make test                              # cd backend && pytest
make lint                              # ruff check . && mypy app   (mypy is non-blocking in CI)
make format                            # black . && ruff check --fix .
cd backend && pytest tests/test_scoring_engine.py -v        # single test file
cd backend && pytest tests/test_scoring_engine.py::test_name # single test
cd backend && uvicorn app.main:app --reload                 # dev API server (port 8000)

# Full stack via Docker (Postgres, Redis, etc.)
make up        # docker-compose up -d
make dev       # up + uvicorn reload
make down

# Frontend (cd frontend)
npm run dev     # Vite dev server (port 5173)
npm run build   # tsc -b && vite build
npm run lint    # eslint
npm test        # node ./scripts/smoke.js  (smoke test, not a unit runner)

# Standalone audit (no backend, no API key needed)
python run_audit.py                                          # heuristic mode
OPENAI_API_KEY=sk-... python run_audit.py --provider openai --model gpt-4o
ANTHROPIC_API_KEY=sk-ant-... python run_audit.py --provider anthropic

# Site context: map a URL N levels down + Claude Code (OAuth) analysis, no API key
python build_context.py https://www.nayuki.io/category/programming --depth 2
python build_context.py https://example.com/docs --map-only          # phase 1 only
python build_context.py https://example.com/docs --no-agent          # skip the agent pass

# MCP server (for local testing)
python -m backend.app.mcp_server
```

Tests run in heuristic mode by default (no API key required). `backend/requirements-ci.txt` is the lighter dependency set used in CI.

## Config

`backend/app/core/config.py` (`Settings`, pydantic-settings) reads from `.env`. Notable: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEFAULT_AI_MODEL`, `WORKSPACE_ROOT` (`.aieo-workspace`), `DATABASE_URL` (Postgres), `REDIS_URL`, `CELERY_BROKER_URL`, DataForSEO/GA/GSC credentials. DB migrations are Alembic under `backend/alembic/`.

## Conventions

- Adding a scoring pattern, agent, or lifecycle command = adding a markdown file under `backend/prompts/`. Reach for Python only for new parsing, integrations, or analyzer dimensions.
- Heuristic scorers in `scoring_engine.py` are stateless module-level `_h_*` functions registered in `_HEURISTIC_SCORERS`, keyed by pattern `name`. Keep them in sync with pattern files so heuristic mode covers every pattern.
- Analyzer modules in `backend/app/analyzers/` are pure-Python scorers (readability, keywords, CRO, SEO) that always run, independent of AI vs heuristic mode — they feed the multi-dimension output.

## Docs

Deeper references live in `docs/`: ARCHITECTURE, PATTERNS, AGENTS, ANALYZERS, INTEGRATIONS, PUBLISHING, WORKFLOW, CLI, API, DEVELOPMENT, SNAPSHOT, SITE_CONTEXT. `PRD-aieo.md` is the full product spec.
