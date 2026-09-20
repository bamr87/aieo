# PRD Lineage

The PRD-lineage feature searches **any repository that delivers a product**, identifies every Product Requirements Document element (and every file that should stay consistent with it), then scores completeness, drift, and lineage so the PRD and its witnesses can be optimized and aligned.

A product repo is one that ships something a user can run, buy, or adopt — an app, library, CLI, site, API, or theme. The engine does not treat the tree as a content article; it treats it as a **spec lineage**.

```bash
# Standalone (no backend, no API key)
python build_prd.py
python build_prd.py /path/to/product-repo --formats json,markdown,mermaid

# Phase 1 only: classify sources
python build_prd.py . --map-only

# Skip the agent pass (heuristic completeness / drift still runs)
python build_prd.py . --no-agent
```

Also available as `aieo prd`, MCP tools `aieo_prd` / `aieo_prd_map` / `aieo_prd_manifest`, and `POST /api/v1/aieo/prd`.

Judgement lives in markdown, not Python: `prompts/agents/prd-lineage-analyst.md` (per source) and `prd-synthesizer.md` (repo level). Python emits *facts* (paths, headings, keyword hits, versions, markdown links). Improvement rules match `.prompts/PRD_IMPROVEMENT_PROMPT.md`.

## Three phases

Each phase's output is the next one's input, and each can be stopped at.

| Phase | What it does | Cost |
| --- | --- | --- |
| **1. Map** (`mapper.py`) | Walk the repo. Classify every product-spec source. Skip vendor trees, secrets, and binaries. | Filesystem only |
| **2. Extract** (`extraction.py`) | Read each source once. Record headings, canonical-element hits, product name/version, and outbound repo links. | No network |
| **3. Analyze** (`agent.py`) | Loop priority sources through the Claude Code CLI over OAuth, then one repo-level synthesis. Always degrades to heuristics. | ≤ `agent_max_sources` + 1 model calls |

`--map-only` stops after phase 1. `--no-agent` still runs phase 3 heuristics so completeness and drift are never empty.

The engine **does not rewrite files**. It returns alignment actions and PRD improvements. Applying them is a separate refactor step.

## Canonical PRD elements

These ids are the catalog the engine looks for in *any* product repo. Requiredness drives the 0–100 completeness score (must 70 / should 25 / could 5).

| Id | Name | Required |
| --- | --- | --- |
| `document_control` | Document Control | must |
| `executive_summary` | Executive Summary | must |
| `problem` | Problem Statement | must |
| `personas` | Users / Personas | must |
| `mvp` | MVP / Scope | must |
| `oos` | Out of Scope | must |
| `success` | Success Criteria | must |
| `ux` | UX / User Flows | should |
| `api` | API | should |
| `nfr` | Non-Functional Requirements | should |
| `edge` | Edge Cases / Dependencies | should |
| `architecture` | Technical Architecture | should |
| `testing` | Testing & Validation | should |
| `security` | Security & Privacy | should |
| `roadmap` | Roadmap | should |
| `risks` | Risks | should |
| `user_stories` | User Stories | could |
| `data_models` | Data Models | could |
| `integrations` | Integrations | could |
| `gtm` | Go-To-Market | could |
| `appendix` | Appendix | could |

A heading is not enough: extraction records a *hit*; the analyst judges whether the body has substance (who/pain/why-now for `problem`, a measurable target for `success`, prioritized scope for `mvp`).

Change what "good" means in the agent prompts. Change what counts as a hit in `elements.py`.

## Lineage witnesses

The canonical PRD is the root. Everything else is a witness that must not contradict it and should cite it.

| Role | Typical files | Why it matters |
| --- | --- | --- |
| `canonical_prd` | `PRD.md`, `PRD-*.md`, `docs/prd.md` | Source of truth |
| `readme` | `README.md` | Public promise |
| `changelog` | `CHANGELOG.md` | What actually shipped |
| `agent_instructions` | `CLAUDE.md`, `AGENTS.md` | How coding agents interpret the product |
| `architecture` / `api` / `install` / `contributing` / `docs` | `docs/*` | Execution docs |
| `packaging` | `package.json`, `pyproject.toml` | Name, version, description |
| `issue_template` | `.github/ISSUE_TEMPLATE/*` | How work is filed vs user stories |
| `prompt_spec` | `backend/prompts/**`, `.prompts/**` | Behavior encoded as prompts |

Broken lineage includes: README that restates the product with no PRD link; CHANGELOG version ahead of the PRD; CLAUDE.md "what this is" that disagrees with the executive summary; packaging name/version that disagrees with the PRD title; docs that specify features the PRD marks out of scope.

## Outputs

`json` is the lossless inventory. `markdown` is the readable brief (coverage table, missing must-elements, drift, actions). `mermaid` is the citation graph.

Manifests land in `<workspace>/.cache/prd/<repo_slug>.json`. Exports default to `<workspace>/prd/<repo_slug>/`.

Each source records `analysis_method`: `agent`, `heuristic`, or `skipped`.

## Surfaces

| Surface | Entry |
| --- | --- |
| Standalone | `python build_prd.py [repo]` |
| CLI | `aieo prd [repo]` |
| MCP | `aieo_prd`, `aieo_prd_map`, `aieo_prd_manifest` |
| REST | `POST /api/v1/aieo/prd`, `GET /api/v1/aieo/prd`, `GET /api/v1/aieo/prd/{slug}` |

Tests are fully offline (fixture product repo + an injectable agent runner) in `backend/tests/test_prd_lineage.py`.
