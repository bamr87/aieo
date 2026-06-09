# Agent Catalog

Prompt agents live in `backend/prompts/agents/` and are executed by `AgentRunner`.

## Available agents

- `content-analyzer`
- `seo-optimizer`
- `meta-creator`
- `internal-linker`
- `keyword-mapper`
- `editor`
- `performance`
- `headline-generator`
- `cro-analyst`
- `landing-page-optimizer`

## API

- `POST /api/v1/aieo/agent/run`
  - body: `agent_name`, `content`, optional `extra_inputs`, optional `model`

## MCP

- `aieo_editor_review`
- `aieo_headline_generate`
