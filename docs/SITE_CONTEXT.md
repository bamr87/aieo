# Site Context

The site-context feature crawls **a URL and the pages N levels below it** into a **contextual dataset**: a link map, per-page content and metadata, a presentation profile (styles, imagery, animation), SEO facts — and an analysis produced by looping every page through a **Claude Code agent over OAuth**.

It is aimed at a *section* of a site rather than a whole domain. Point it at an index like `https://www.nayuki.io/category/programming` and it maps the index, follows it to each item page, and builds one dataset describing the whole neighbourhood.

```bash
# Standalone (no backend, no API key) — the simplest path
python build_context.py https://www.nayuki.io/category/programming

# Two levels down, every format
python build_context.py https://www.nayuki.io/category/programming \
    --depth 2 --formats json,markdown,html,mermaid --output ./context

# Just the shape: phase 1 only, no extraction, no agent calls
python build_context.py https://example.com/docs --map-only

# Stay inside the seed's own path, and skip the agent pass entirely
python build_context.py https://example.com/docs --scope path --no-agent
```

## Three phases

Each phase's output is the next one's input, and each can be stopped at.

| Phase | What it does | Cost |
| --- | --- | --- |
| **1. Map** (`link_map.py`) | Level-ordered BFS from the seed. Records nodes (with depth, parents, anchor texts), edges, off-scope references and asset-reference counts. Bodies land in the cache. | One GET per page |
| **2. Extract** (`extraction.py`) | Reads each cached body back — **no second request** — and derives content, metadata, SEO facts and the presentation profile. | Only linked CSS (fetched once per site) |
| **3. Analyze** (`agent.py`) | Loops the pages through the Claude Code CLI over OAuth, then one site-level synthesis call. | ≤ `agent_max_pages` + 1 model calls |

`--map-only` stops after phase 1. `--no-agent` stops after phase 2.

## Phase 1 — mapping links and references

Depth is measured **from the seed**: depth 0 is the seed page, `--depth 2` walks two levels of links below it. Each level has its own budget (`--max-per-level`), so one huge index cannot starve the deeper levels.

Scope decides what counts as "inside":

| `--scope` | Meaning |
| --- | --- |
| `host` (default) | Same site (`www.` ignored). A category page's items usually live elsewhere on the host, so this is the useful default. |
| `domain` | Same registrable host **and** its subdomains. |
| `path` | Only URLs under the seed's own path — `--scope path` on `/docs` never leaves `/docs`. |

Off-scope links are always **recorded** as references (rolled up by domain); they are only crawled with `--include-external`.

Two deliberate differences from the snapshot crawler ([SNAPSHOT.md](SNAPSHOT.md)):

* it does **not** deny `/category/`, `/tag/` or `/page/` — those prefixes are
exactly where a section seed and its items live. Only genuine non-content paths (`/assets/`, `/static/`, `/cdn-cgi/`) are skipped by default;
* only real **pagination** traps (`/page/2`, `?page=3`) are dropped, not
`/page/<slug>` item URLs or dated post paths (pass `skip_pagination: false` via the API/MCP to keep even those).

`robots.txt` is honoured by default (`--no-robots` to ignore), including `Crawl-delay`. `--follow-sitemap` additionally seeds level 1 with in-scope `sitemap.xml` URLs, which picks up pages an index paginates away.

## Phase 2 — extraction and metadata analysis

Per page, the dataset records:

**Content** — main-content text (nav/header/footer/chrome stripped, same extractor as the snapshot feature), word count, reading time, heading outline, tables, lists, summary. `--full-page` keeps the chrome.

**Metadata** — title, description, lang, canonical, author, dates, tags, categories, JSON-LD `@type`s, Open Graph, generator.

**SEO facts** (`seo.py`) — title/description lengths with status, canonical self-reference, `robots` meta and indexability, viewport, charset, hreflang, feeds, `rel=prev/next`, favicon, AMP, Open Graph and Twitter-card completeness, structured-data types plus JSON parse errors, heading outline validity (`h1` count, level skips), image alt coverage, internal/external link counts — and a list of concrete **issues** (`severity`, `code`, `message`).

**Interactivity** (`presentation.py`) — the "what you can *do* here" layer, and the one prose extractors throw away. Controls and their types, the labels that name them, sliders, file uploads, demo section headings, event listeners, and whether the demo ships `hidden` and is revealed by script (progressive enhancement). Two rules make this work at all:

- `<form>` subtrees and `hidden` demo containers are **kept as content** when
`keep_interactive` is on (the default for context builds; snapshots still strip them). Without that, a page whose payload is a live tool extracts as a section heading with nothing under it — measured on one real page, 14 tables and every control were deleted before extraction.
- Same-host **JavaScript is fetched** (once per site, like the CSS) and scanned.
Motion driven by a `requestAnimationFrame` loop, scripted canvas drawing or scripted SVG lives only in that file; without reading it, a page whose entire point is an animation profiles as `"static: no motion detected"`.

Third-party scripts (analytics, ads, CDN libraries) are skipped — they are huge, they are not the site's own behaviour, and their libraries are already fingerprinted from the tag's `src`. `--no-js` skips script fetching, `--no-interactive` restores the strip-it-all behaviour.

**Resources** (`resources.py`) — every link is classified before it reaches the frontier. A link to `ellipticcurve.py` or `QrCode.java` is a **download**, not a page: crawling it costs a request and yields "not HTML", and leaving it in the link graph inflates the internal-link counts. Source files (30+ languages, each labelled), archives, documents, data files, video and audio become typed entries in the asset inventory instead. On one real site that reclassified 342 source downloads across 12 languages that had been recorded as crawlable pages.

**Presentation** (`presentation.py`) — the "what it looks like" layer:

* *styles*: linked + inline CSS, colour palette (weighted), CSS custom
properties, font stacks and `@font-face` count, media queries and breakpoints, container queries, flex/grid usage, dark-mode support, `theme-color`, detected CSS frameworks (Tailwind, Bootstrap, Bulma, …);
* *images*: every `<img>` with alt/dimensions/`loading`/`srcset`, format
histogram, alt and lazy-load coverage, `<picture>` sources, inline SVG count, CSS `background-image` references, icons, `og:image`;
* *animation*: `@keyframes` names, `animation`/`transition`/`transform`
declaration counts, `will-change`, smooth scrolling, whether a `prefers-reduced-motion` guard exists, motion libraries (GSAP, Framer Motion, Lottie, AOS, Three.js, ScrollReveal, Swiper, …), `<video>` (autoplay/loop/ muted), `<canvas>`, SVG SMIL, Web Animations API, `requestAnimationFrame`, `IntersectionObserver` and scroll listeners — plus short readable `signals`;
* *scripts*: external/inline counts, async/defer/module, JSON-LD blocks, and
  detected JS frameworks (Next.js, React, Vue, Svelte, Astro, htmx, …).

Linked stylesheets are fetched **once per crawl** and shared across pages — a theme's CSS is the same file on every page, and most real animation lives there. `--no-css` skips the fetch (inline CSS only); `--no-presentation` skips the whole profile.

> Python emits *facts*, never scores. Per the project's central rule, scoring
> criteria live in `backend/prompts/` — the qualitative read is the agent's job.

## Phase 3 — the Claude Code agent loop (OAuth)

The analysis runs through the locally authenticated **Claude Code CLI** (`claude -p --output-format json`), the same OAuth path as the `claude-cli` scoring provider ([CLAUDE_CLI_PROVIDER.md](CLAUDE_CLI_PROVIDER.md)). **No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is involved.**

* **Per page** → `prompts/agents/site-context-analyst.md` returns `page_type`,
`topics`, `entities`, `audience`, `purpose`, `summary`, `key_points`, `content_quality` (depth/structure/citability), `seo_assessment`, `design_notes` (style/imagery/motion), `relationships`, `keywords`, `confidence`.
* **Whole site** → `prompts/agents/site-context-synthesizer.md` returns
`site_purpose`, `audience`, `content_taxonomy`, `information_architecture`, `design_system`, `seo_posture`, `topic_coverage`, `coverage_gaps` and a `context_brief` — the dense paragraph you paste into another tool to hand it working context on the site.

Changing what the agent looks for means editing those markdown files, not Python.

The loop is bounded on every axis:

| Guard | Default | Flag |
| --- | --- | --- |
| Pages that get a real call (seed first, then hubs and substantial pages) | 25 | `--agent-pages` |
| Concurrent calls | 3 | `--agent-concurrency` |
| Per-call timeout | 180s | `--agent-timeout` |
| Text sent per page | 6000 chars | `agent_max_chars` (API) |
| Consecutive failures before the breaker trips | 3 | — |

Every page the agent does not (or cannot) analyze still gets a deterministic heuristic record, so the dataset is never half-empty. Each node carries `analysis_method`: `agent`, `heuristic` or `skipped`; the run reports `agent`, `mixed` or `heuristic` overall. If the CLI is missing or logged out, the whole build still succeeds in heuristic mode and says so.

## JavaScript rendering (optional)

A static fetch sees what the server sends, which on script-built pages is not what a reader sees. Measured on one page: the served HTML carried 17 tables and no buttons; the rendered DOM had 23 tables and 78 buttons.

`--render` drives headless Chromium through Playwright and crawls the post-JavaScript DOM — so JS-injected links are followed and JS-built content is extracted. It is strictly opt-in, because it is a heavy dependency (a browser download, not just a wheel), an order of magnitude slower than a GET, and it forfeits conditional-GET incrementality (a rendered DOM has no ETag; rendered bodies are cached under a separate key so re-exports still work offline). If Playwright is missing or the browser will not launch, the crawl says so in `phases.map.render_fallback` and continues with static fetches.

```bash
pip install playwright && playwright install chromium
python build_context.py https://example.com/app --render --render-wait 1200
```

The same SSRF guard applies: every URL is validated before the browser is pointed at it.

## Optional libraries (`adapters.py`)

Reading arbitrary websites is a variability problem, and mature libraries encode years of it. Each is used **only if installed**, and every failure falls back to the built-in path — the same "stdlib floor, upgrade if present" shape the PDF exporter uses.

| Library | What it upgrades | Why |
| --- | --- | --- |
| `trafilatura` | Main-content extraction | The strongest general article extractor in Python; powers FineWeb/RefinedWeb |
| `extruct` | Structured data | Adds Microdata, RDFa and microformats — a JSON-LD-only reader misses them |
| `protego` | robots.txt | Wildcards, `Allow` precedence, per-agent `Crawl-delay`; `urllib.robotparser` handles only the basics |

```bash
pip install trafilatura extruct protego     # all optional
python build_context.py <url> --extractor builtin   # or ignore them: --no-libraries
```

**Extraction is deliberately not delegated wholesale to trafilatura.** The 2026 WCXB benchmark puts it at F1 ≈ 0.92 on articles but **0.52 on collections** and **0.55 on listings** — and a context build is *seeded* on exactly those. A category index is nothing but a link list, which article extractors are built to discard as boilerplate. So `--extractor auto` (the default) uses the library on article-shaped pages and the built-in content-root path on hubs, and it only accepts the library's output when it finds at least as much as the built-in path did. `builtin` and `trafilatura` force one engine for every page.

## Output formats

| Format | Ext | Notes |
| --- | --- | --- |
| `json` | `.json` | The lossless dataset — every other format derives from it |
| `markdown` | `.md` | Readable context brief: clusters, link map, presentation, interactive surface, SEO, per-page cards |
| `html` | `.html` | Self-contained, inert review page (no scripts), light/dark aware |
| `mermaid` | `.mmd` | The link map as a `graph LR` you can paste into any Mermaid renderer |

Stored datasets re-render offline from the manifest, so any format can be produced later without re-crawling.

## Caching

Bodies live in the **snapshot crawler's cache** (`<workspace>/.cache/snapshots/<site_slug>/`), so a context build and a `crawl_site.py` snapshot of the same host share one conditional-GET cache and neither re-downloads what the other already has. Manifests live beside it in `context/<context_key>.json`, where the key is derived from the seed path — `/category/programming` → `category-programming-4f3a1c2b` — so one site can hold many contexts.

`--refresh` ignores validators, `--no-cache` purges and rebuilds, `--ttl N` skips revalidation for entries younger than N seconds.

**Broken revalidation.** Some servers answer a conditional GET with `200 OK` and an *empty body* instead of `304 Not Modified` (observed live on nayuki.io). Taken at face value that overwrites every cached body with nothing, so the next run returns an empty dataset — quietly, with no error. Both the page fetch and the stylesheet/script fetch treat an empty `200` answer to a conditional GET as the `304` it meant to be, never let an empty body replace a good cached one, and repair a cache already poisoned by an earlier run with an unconditional retry.

## The four surfaces

All four are thin wrappers over one service, `SiteContextService` ([backend/app/services/site_context/](../backend/app/services/site_context/)).

| Surface | How |
| --- | --- |
| **Standalone script** | `python build_context.py <url> --depth 2` |
| **CLI** | `aieo context <url> --depth 2` (add `--remote` to call the API) |
| **MCP** | `aieo_site_context`, `aieo_context_map`, `aieo_context_manifest` |
| **REST** | `POST /api/v1/aieo/context`, `GET /aieo/context`, `GET /aieo/context/{site_slug}/{context_key}`, `GET …/export/{fmt}` |

```bash
# batch several seeds
python build_context.py --seeds seeds.txt --depth 1

# REST
curl -X POST localhost:8000/api/v1/aieo/context -H "X-API-Key: $AIEO_API_KEY" \
  -H 'content-type: application/json' \
  -d '{"seed_url":"https://www.nayuki.io/category/programming","depth":2,"formats":["json","markdown"]}'
```

## Safety

Every request — including each redirect hop — goes through the snapshot fetcher's SSRF guard, which resolves the target and rejects loopback, private, link-local and reserved addresses (IPv4 and IPv6), then pins the connection to the validated IP. Set `AIEO_SNAPSHOT_ALLOW_PRIVATE=1` only for local testing. Site slugs and context keys are validated before they are joined into a filesystem path. HTML exports are inert: no scripts, and outbound links carry `rel="nofollow noopener"`.

## Tests

`backend/tests/test_site_context.py` runs fully offline: a fixture site (a `/category/<name>` index whose items live under `/page/<slug>`, plus a page whose payload is a live tool) is served from 127.0.0.1, and every external dependency is stubbed — the Claude Code CLI by a fake executable (so the OAuth loop, per-page budget, missing binary and failure circuit breaker are exercised without calling a model), the browser by a stub renderer, and trafilatura/extruct/protego by stub modules, so the adapter wiring is tested without installing any of them.

```bash
cd backend && pytest tests/test_site_context.py -v
```
