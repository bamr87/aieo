# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Site Snapshot**: crawl a Jekyll/static site into a cached, offline, multi-format copy (text/json/markdown/html/pdf/zip-bundle) for review, analysis, and backup. New `backend/app/services/site_snapshot/` package (`SiteSnapshotService`), standalone `crawl_site.py`, CLI `aieo crawl`, MCP tools `aieo_crawl_site`/`aieo_crawl_manifest`, and REST `POST /api/v1/aieo/snapshot` (+ manifest/export GETs). Jekyll-tuned discovery (sitemap.xml → feed.xml → robots.txt → link BFS), incremental conditional-GET caching (ETag/Last-Modified + content hashing), DNS-pinned SSRF guard, stdlib-only PDF writer, and offline tests. See `docs/SNAPSHOT.md`.
- Workspace service and API (`/aieo/workspace/*`) with seeded context templates under `.aieo-workspace`
- Content lifecycle endpoints (`/aieo/research`, `/aieo/write`, `/aieo/rewrite`, `/aieo/analyze-existing`, `/aieo/scrub`)
- Landing and performance endpoints (`/aieo/landing/*`, `/aieo/priorities`, `/aieo/data/*`)
- Integration layer for GA4, GSC, DataForSEO with filesystem cache
- Publishing layer with WordPress adapter and `/aieo/publish/wordpress`
- Agent prompt collections in `backend/prompts/agents/` and command prompts in `backend/prompts/commands/`
- Analyzer package (`backend/app/analyzers`) and multi-dimension scoring in `ScoringEngine`
- Frontend workflow routes/pages: workspace, topics, research, drafts, rewrites, published, landing, performance, agents
- New MCP tools for lifecycle, workspace, analyzers, and publishing
- New workflow metadata models and Alembic migration `002_workflow_metadata.py`
- Backend tests for workspace, analyzers, lifecycle services, and data/publish services
- Frontend smoke test script (`frontend/scripts/smoke.js`)

### Changed
- `tools.aieo_runner` now supports workflow commands (`research`, `write`, `rewrite`, `analyze`, `scrub`, `priorities`)
- App version bumped to `0.3.0`

## [0.2.0] - 2026-03-28

### Added
- **PRD v2.0**: Major update to AIEO Studio – AI Engine Optimization Platform
  - Executive Summary with full-cycle platform positioning
  - Intelligent Refactor Agent (P0 feature) for production-ready patches
  - 6 new AEO-specific patterns: JSON-LD Schema, Semantic HTML, E-E-A-T Signals, Substantiated Claims, Recursive Q&A, Answer-First Structure
  - GitHub / Copilot / MCP integration as first-class features
  - zer0-mistakes.com as reference implementation (target: 98+/100)
  - Hybrid SEO + AEO scope (traditional SEO now in-scope)
  - Updated scoring rubric with 16 patterns (10 original + 6 new)
  - Revised roadmap: MVP Q2 2026, Growth Q3 2026, Scale Q4 2026, Enterprise 2027
- MCP server implementation (`backend/app/mcp_server.py`)
- Prompt loader service for scoring rubric and system prompts
- Screenshot service for visual auditing
- Report generation tooling (`generate_reports.py`, `run_audit.py`)
- MCP client audit tool (`mcp_client_audit.py`)
- Scoring prompts and patterns (`backend/prompts/`)
- Backend Dockerfile for containerized deployment
- MCP requirements file (`backend/requirements-mcp.txt`)
- Sample audit reports (`reports/`)

### Changed
- Scoring engine refactored with updated pattern detection
- README updated with AIEO Studio branding and expanded documentation
- Architecture docs updated for MCP and refactoring engine
- CLI docs expanded with new commands
- Development docs updated with MCP setup instructions
- Patterns docs expanded with AEO-specific patterns
- Docker Compose updated with additional services
- Backend dependencies updated

### Documentation
- PRD expanded from v1.2 to v2.0 with 21 sections (0–20)
- New personas: Indie Developer, Content Agency PM, SEO Specialist, Open-Source Maintainer
- New user stories: Repo Refactor via PR, Jekyll Theme Optimization, MCP Agent Integration
- Updated glossary with AEO, GEO, MCP, JSON-LD, E-E-A-T terms
- Decision log updated with 7 new decisions

## [0.1.0] - 2025-12-28

### Added
- Initial alpha release
- Core audit functionality
- Scoring engine with 10 patterns
- Content parser for markdown and HTML
- Basic optimization service
- Web UI MVP
- CLI tool MVP

### Technical
- FastAPI backend
- React + TypeScript frontend
- PostgreSQL database
- Redis caching
- Qdrant vector database (optional)
- Docker Compose for local development
- Alembic migrations
- Pytest test suite

### Known Limitations
- Citation detection requires API access to AI engines (placeholder)
- Optimization requires OpenAI/Anthropic API keys
- Benchmark uses placeholder percentile calculation
- Some features require database setup

---

## Version History

- **0.2.0** (2026-03-28): AIEO Studio v2.0 – Refactor Agent, MCP integration, 6 new AEO patterns, PRD v2.0
- **0.1.0** (2025-12-28): Initial alpha release

---

## Upcoming Features

See [PRD-aieo.md](PRD-aieo.md) for roadmap and planned features.

### Planned for Beta
- Full citation detection for 6 AI engines
- Citation tracking dashboard
- Batch processing
- Webhook alerts
- Enhanced optimization

### Planned for v1.0
- WordPress plugin
- CMS integrations
- Team features
- Advanced analytics

