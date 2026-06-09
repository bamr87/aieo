# AIEO — AI Engine Optimization

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)

**AIEO** is an AI-native analysis engine that scores, reviews, and optimizes website content for citability by AI engines — ChatGPT, Claude, Grok, Gemini, Perplexity, and others. It replaces traditional SEO thinking with a prompt-engineered, agent-orchestrated workflow where AI models evaluate your content the same way they would when deciding whether to cite it.

## Unified Content Platform (AIEO + SEO Machine capabilities)

AIEO now includes a full content lifecycle layer in addition to classic audit/optimize:

- Workspace management in `.aieo-workspace/` (`context/`, `topics/`, `research/`, `drafts/`, `rewrites/`, `published/`, `landing-pages/`)
- Research and writing endpoints: `/aieo/research`, `/aieo/write`, `/aieo/rewrite`, `/aieo/analyze-existing`, `/aieo/scrub`
- Specialized agents via `AgentRunner`: content-analyzer, seo-optimizer, meta-creator, internal-linker, keyword-mapper, editor, performance, headline-generator, cro-analyst, landing-page-optimizer
- Multi-dimension scoring output (AIEO, SEO, Readability, Humanity, CRO) with analyzer modules under `backend/app/analyzers/`
- Data connectors for GA4, GSC, and DataForSEO under `backend/app/integrations/`
- WordPress publishing via `/aieo/publish/wordpress` and `backend/app/publishers/wordpress_publisher.py`
- Expanded MCP tools (`aieo_research`, `aieo_write`, `aieo_rewrite`, `aieo_analyze_existing`, `aieo_scrub`, `aieo_priorities`, `aieo_landing_audit`, `aieo_workspace_*`, `aieo_publish_wordpress`)

Frontend routes now expose the full workflow: `/workspace`, `/topics`, `/research`, `/drafts`, `/rewrites`, `/published`, `/landing-pages`, `/performance`, `/agents`.

---

## The Problem

Search engines are no longer the primary discovery layer. AI engines are. When someone asks ChatGPT or Claude a question, the AI decides — in real time — which content to cite, synthesize, and recommend. Content optimized for Google's crawlers is invisible to this new system.

**AIEO gives you a way to see your content through the eyes of AI engines** — and fix what they can't parse, cite, or trust.

## How It Works

AIEO is built on three architectural principles:

### 1. Prompt-Driven Scoring (No Hardcoded Rules)

All scoring criteria, pattern definitions, and evaluation instructions live in external **prompt files** — not in Python code. The AI reads these prompts at runtime and evaluates content contextually:

```
backend/prompts/
├── system.md                  # AI's role and evaluation principles
├── scoring_rubric.md          # Output format, scoring rules, anti-patterns
└── patterns/
    ├── structured_data.md     # Weight: 20 — tables, lists, headers
    ├── entity_density.md      # Weight: 15 — named entities per 100 words
    ├── comparison_tables.md   # Weight: 15 — structured X vs Y analysis
    ├── recursive_depth.md     # Weight: 15 — follow-up Q&A, nested depth
    ├── faq_injection.md       # Weight: 15 — question-answer formatting
    ├── citation_hooks.md      # Weight: 10 — source attributions
    ├── temporal_anchoring.md  # Weight: 10 — dates, versions, freshness
    ├── definitional_precision.md  # Weight: 10 — explicit definitions
    ├── meta_context.md        # Weight: 10 — "why this matters" framing
    └── procedural_clarity.md  # Weight: 5 — step-by-step instructions
```

To change how scoring works, **edit a markdown file**. No code changes needed. Add a new pattern by dropping a new `.md` file in `patterns/` with YAML frontmatter:

```yaml
---
name: my_new_pattern
display_name: My New Pattern
weight: 10
max_score: 10
---
## What to Evaluate
[your criteria here]
```

### 2. AI-Orchestrated Analysis

When an API key is configured (OpenAI or Anthropic), the engine sends your content and the assembled prompts to the AI model. The model evaluates every pattern contextually — understanding that a personal blog is scored differently from technical documentation — and returns structured JSON with:

- **Per-pattern scores** with evidence quoted from the actual content
- **Specific, actionable recommendations** for each pattern (not generic advice)
- **Content type detection** (article, landing page, documentation, product page, FAQ, etc.)
- **Anti-pattern detection** (keyword stuffing, pattern cramming, citation fishing)
- **Overall assessment** summarizing strengths and weaknesses

When no API key is available, the engine falls back to lightweight heuristic scoring using structural analysis.

### 3. MCP Server (Model Context Protocol)

AIEO exposes its capabilities as **MCP tools** that any AI agent can call — Claude Desktop, VS Code Copilot, custom agent workflows, or any MCP-compatible client:

| Tool | Description |
|------|-------------|
| `aieo_score_content` | Score raw content (markdown or HTML) against all AIEO patterns |
| `aieo_audit_url` | Fetch a URL, parse its content, and return a full scoring analysis |
| `aieo_list_patterns` | List all active patterns with names, weights, and max scores |
| `aieo_get_pattern` | Get the full evaluation criteria for a specific pattern |

This means you can ask an AI agent: *"Audit my website and tell me what to fix"* — and it calls AIEO's MCP tools to do the analysis, then gives you a report in natural language.

---

## What AIEO Analyzes

AIEO parses and extracts from your website:

| Layer | What's Analyzed | Why It Matters |
|-------|----------------|----------------|
| **Structure** | Headers, tables, lists, ordered/unordered sections | AI engines extract structured data preferentially |
| **Entities** | Named people, organizations, products, locations, dates | Specific entities make content uniquely citable |
| **Citations** | Source attributions, external links, evidence markers | AI engines trust content that cites verifiable sources |
| **Questions** | FAQ sections, question headers, follow-up depth | AI engines match content to user queries |
| **Temporal** | Dates, version numbers, freshness signals | AI engines assess information currency |
| **Definitions** | Explicit definitions, glossaries, term explanations | AI engines quote definitions directly |
| **Comparisons** | Tables comparing options, pro/con lists | AI engines serve these for "X vs Y" queries |
| **Procedures** | Step-by-step instructions, numbered processes | AI engines extract these for "how to" queries |
| **Links** | Internal/external link graph, anchor text | Citation credibility and reference depth |
| **Anti-patterns** | Keyword stuffing, over-optimization, missing structure | Signals that reduce trust and citability |

---

## Quick Start

### Standalone Audit (No Backend Required)

The fastest path — audit websites from the command line:

```bash
# Set up a lightweight environment
python3 -m venv venv && source venv/bin/activate
pip install httpx beautifulsoup4 markdown html2text

# Add URLs to sites.txt (one per line), then:
python run_audit.py
```

This runs in **heuristic mode** (structural analysis, no API calls). To enable AI-driven scoring:

```bash
# OpenAI
OPENAI_API_KEY=sk-... python run_audit.py --provider openai --model gpt-4o

# Anthropic
ANTHROPIC_API_KEY=sk-ant-... python run_audit.py --provider anthropic
```

Full CLI options:

```
python run_audit.py [OPTIONS]
  --provider [openai|anthropic]   AI provider
  --model MODEL                   Model name (gpt-4o, claude-sonnet-4-20250514, etc.)
  --api-key KEY                   API key (or set via env var)
  --sites FILE                    Path to URL list (default: sites.txt)
  --output DIR                    Output directory (default: auto temp dir)
```

### MCP Integration (Agent Workflows)

Configure AIEO as an MCP server in your AI tool:

**VS Code / Copilot** (`.vscode/mcp.json`):
```json
{
  "mcpServers": {
    "aieo-scoring": {
      "command": "python",
      "args": ["-m", "backend.app.mcp_server"],
      "cwd": "${workspaceFolder}",
      "env": {
        "OPENAI_API_KEY": "${env:OPENAI_API_KEY}",
        "ANTHROPIC_API_KEY": "${env:ANTHROPIC_API_KEY}"
      }
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "aieo": {
      "command": "python",
      "args": ["-m", "backend.app.mcp_server"],
      "cwd": "/path/to/aieo"
    }
  }
}
```

Then ask your AI agent:
- *"Use AIEO to audit https://example.com and tell me what to improve"*
- *"Score this markdown file for AI citability"*
- *"What AIEO patterns is my content missing?"*

### Full Stack (API + Web UI)

For the complete platform with dashboard, citation tracking, and REST API:

```bash
# Install
./scripts/install.sh     # Linux/macOS
python scripts/install.py  # Windows

# Configure
cp env.example .env
# Edit .env with your API keys

# Start
cd backend && source venv/bin/activate && uvicorn app.main:app --reload
cd frontend && npm run dev
```

- Web UI: http://localhost:5173
- API Docs: http://localhost:8000/docs

---

## Project Structure

```
aieo/
├── backend/
│   ├── prompts/                    # Prompt engineering — the scoring brain
│   │   ├── system.md              # AI role and evaluation principles
│   │   ├── scoring_rubric.md      # Output format and scoring rules
│   │   └── patterns/             # 10 pattern definition files
│   ├── app/
│   │   ├── services/
│   │   │   ├── scoring_engine.py  # AI-orchestrated scoring engine
│   │   │   ├── prompt_loader.py   # Loads and assembles prompt files
│   │   │   ├── content_parser.py  # HTML/MD → structured data extraction
│   │   │   ├── ai_service.py      # OpenAI + Anthropic integration
│   │   │   ├── audit_service.py   # Full-stack audit orchestration
│   │   │   └── optimize_service.py
│   │   ├── mcp_server.py          # MCP tool server
│   │   ├── api/v1/               # REST API endpoints
│   │   ├── core/                 # Config, security, middleware
│   │   ├── models/               # Database models
│   │   └── tasks/                # Async task queue (Celery)
│   └── tests/
├── frontend/                     # React + TypeScript dashboard
├── cli/                          # Python CLI (aieo audit, aieo optimize)
├── run_audit.py                  # Standalone batch audit script
├── sites.txt                     # URL list for batch auditing
├── .vscode/mcp.json              # MCP server configuration
└── docker-compose.yml
```

---

## Scoring Output

Every audit produces a structured result:

```json
{
  "score": 62.5,
  "grade": "C",
  "scoring_method": "ai",
  "content_type": "landing_page",
  "overall_assessment": "Strong entity density and structured data, but lacks FAQ sections and temporal anchoring...",
  "pattern_scores": {
    "structured_data": {
      "score": 16,
      "max": 20,
      "detected": true,
      "evidence": ["3 tables found with clear headers", "5 bullet lists organizing service features"],
      "recommendation": "Add a comparison table for your service tiers."
    },
    "entity_density": {
      "score": 12,
      "max": 15,
      "detected": true,
      "evidence": ["'Sopris Accounting', 'Carbondale, Colorado', 'CPA' — 8 entities in 725 words"],
      "recommendation": "Add founding year, team member names, and specific certification bodies."
    }
  },
  "gaps": [
    {
      "severity": "high",
      "category": "faq_injection",
      "description": "Add a FAQ section answering: 'What does a CPA do?', 'How much does tax preparation cost?', 'What documents do I need?'"
    }
  ],
  "anti_pattern_penalties": 0,
  "word_count": 725
}
```

---

## Adding or Changing Patterns

AIEO's scoring behavior is entirely controlled by prompt files. To modify:

| Goal | Action |
|------|--------|
| **Add a new pattern** | Create `backend/prompts/patterns/your_pattern.md` with YAML frontmatter |
| **Change scoring criteria** | Edit the relevant pattern `.md` file |
| **Adjust weights** | Change `weight:` in the pattern's YAML frontmatter |
| **Change the AI's evaluation approach** | Edit `backend/prompts/system.md` |
| **Change output format** | Edit `backend/prompts/scoring_rubric.md` |
| **Add anti-pattern rules** | Add to the anti-patterns section in `scoring_rubric.md` |

No Python code changes required for any of the above.

---

## Development

```bash
# Run tests (heuristic mode, no API key needed)
cd backend && python -m pytest tests/ -v

# Run a specific test
python -m pytest tests/test_scoring_engine.py -v

# Start MCP server directly (for testing)
python -m backend.app.mcp_server
```

## Documentation

- [Installation Guide](INSTALL.md)
- [API Reference](docs/API.md)
- [CLI Guide](docs/CLI.md)
- [AIEO Patterns](docs/PATTERNS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Product Requirements](PRD-aieo.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards, and [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## License

MIT — see [LICENSE](LICENSE).

