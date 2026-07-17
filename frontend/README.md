# AIEO Frontend

A React 19 + TypeScript + Vite single-page app to **run, view, interact with, and manage** the AIEO tool and its results. It talks to the FastAPI backend (`/api/v1/aieo/*`).

## Run it

```bash
# 1) Backend (from repo root) — heuristic mode needs no API key.
#    Minimal headless run on sqlite (no Postgres/Redis required):
cd backend && AIEO_HEADLESS=1 DATABASE_URL="sqlite:///./aieo_dev.db" REDIS_URL="" \
  uvicorn app.main:app --port 8000
#    (For AI scoring set OPENAI_API_KEY / ANTHROPIC_API_KEY, or pick "Claude Code (OAuth)" in the UI.)

# 2) Frontend
cd frontend && npm install && npm run dev      # http://localhost:5173
```

Then open the app, go to **Settings**, and set an API key — every backend endpoint requires an `X-API-Key` header. For local dev, click **“Use dev key”** (any 11+ char string is accepted by the simple verifier). The base URL defaults to `http://localhost:8000/api/v1`; override with `VITE_API_BASE_URL` in `.env.local`.

## What's here

- **Score & optimize** — Audit (score + dimensions radar + pattern breakdown + gaps with one-click agent fixes + local audit history), Optimize (before/after with rendered diff), Patterns library + preview-apply, Agents playground.
- **Create** — Topics, Research, Drafts (with agent assists), Rewrites (side-by-side), Landing pages, and a filesystem Workspace browser/editor.
- **Analyze & publish** — Citations dashboard, Performance (GA4/GSC/SERP), Published artifacts + WordPress publish.
- **Settings** — API key, default **provider** (Auto / Claude Code OAuth / OpenAI / Anthropic / Heuristic) + model, and a connection test.

## Architecture

- **`src/components/ui/`** — the design system (Button, Card, Field/Input/Textarea/Select, Badge, ScoreRing/Meter, Modal, Tabs, JsonView, Markdown/ContentViewer, …) built on Tailwind v4 design tokens defined in `src/index.css`.
- **`src/components/AppShell.tsx`** — grouped responsive sidebar + topbar (provider selector, API-key status).
- **`src/services/`** — typed API client (`api.ts`, normalized `ApiError`, timeouts) + one module per area; import via the `services` barrel.
- **`src/hooks/`** — `useSettings` (key/provider/model), `useToast`, `useAsyncAction` (loading/error), `useAuditHistory`.
- **`src/types/index.ts`** — request/response DTOs.

## Scripts

```bash
npm run dev      # Vite dev server (5173)
npm run build    # tsc -b && vite build
npm run lint     # eslint
```
