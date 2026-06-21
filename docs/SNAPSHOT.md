# Site Snapshot

The site snapshot feature crawls a Jekyll/static site and produces a
**comprehensive, lightweight, offline copy of the entire site's content** — a
single file (or a zip package) you can use for review, analysis, or backup. It
is independent of the AIEO scoring engine: no API key, no database, no AI model.

Discovery is tuned for Jekyll (`sitemap.xml` → `feed.xml` → `robots.txt` →
same-domain link following), every page is cached on disk so re-runs only
re-download what changed, and the snapshot can be exported as **text, JSON,
markdown, HTML, PDF, or a zip bundle**.

## Quick start

```bash
# Standalone (no backend, no API key) — the simplest path
python crawl_site.py https://bashconsultants.com

# Pick formats and an output directory
python crawl_site.py https://bashconsultants.com \
    --formats text,json,markdown,html,pdf,bundle --output ./snapshot

# Re-run later: unchanged pages come back via HTTP 304 / content-hash and are
# served from cache, so only changed/new pages are re-fetched.
python crawl_site.py https://bashconsultants.com

# Force a full re-fetch / rebuild
python crawl_site.py https://bashconsultants.com --refresh   # ignore validators
python crawl_site.py https://bashconsultants.com --no-cache  # purge + rebuild

# Batch several sites from a file (one URL per line)
python crawl_site.py --sites sites.txt --formats html,json
```

## The four surfaces

All four are thin wrappers over one service, `SiteSnapshotService`
([backend/app/services/site_snapshot/](../backend/app/services/site_snapshot/)).

| Surface | How |
| --- | --- |
| **Standalone script** | `python crawl_site.py <url>` — offline, lean deps only |
| **CLI** | `aieo crawl <url> --formats html,json` (add `--remote` to call the API) |
| **MCP** | tools `aieo_crawl_site` and `aieo_crawl_manifest` |
| **REST** | `POST /api/v1/aieo/snapshot`, `GET /api/v1/aieo/snapshot/{slug}/manifest`, `GET …/export/{fmt}` |

## Output formats

Every format is rendered from one in-memory model, so they stay consistent.

| Format | Ext | Single file | Notes |
| --- | --- | --- | --- |
| `text` | `.txt` | ✓ | Grep/diff-friendly outline + body; ideal for pasting into an LLM |
| `json` | `.json` | ✓ | Lossless manifest; the source every other format is derived from |
| `markdown` | `.md` | ✓ | One "book" with an anchored table of contents |
| `html` | `.html` | ✓ | Self-contained, navigable (sticky sidebar); inline CSS, no JS, no external assets except images |
| `pdf` | `.pdf` | ✓ | Pure-stdlib writer (zero new deps); upgrades to `reportlab`/Playwright automatically if installed |
| `bundle` | `.zip` | ✓ (package) | A zip of html + markdown + json + text + README — the "package" deliverable |

For a **fully offline** HTML/bundle that also embeds images, add
`--include-assets` (images are downloaded, size-capped, and inlined as data
URIs). Note this trades the "lightweight" goal for completeness: base64-inlining
full-resolution images can produce a very large single file on image-heavy
sites, so it is opt-in. Without it, the default HTML stays small (images are
referenced by their absolute URL and load over the network).

## Content extraction (de-duplication)

By default the snapshot records each page's **main content only** — it extracts
from the page's main-content container (`<main>`, `[role=main]`, `<article>`,
`#main-content`, `.page__content`, …) and strips nav, header, footer, sidebars,
modals, cookie banners, and in-page tables-of-contents. Without this, a theme's
chrome is repeated on every page: on a real Jekyll site that was **~56% of the
total word count**. Main-content extraction cut it to **<1%** and roughly halved
the HTML/JSON output.

Each page records which container it used in `content_root` (e.g. `main`,
`#main-content`, or `body` when no semantic container was found and the whole
body minus landmarks is used). Pass `--full-page` (CLI/script) or
`strip_boilerplate: false` (REST/MCP) to keep the full page chrome instead.

`content_hash` is always computed over the **raw** HTML (so caching/change
detection is unaffected), while `text`/`word_count` reflect the extracted content.

## Caching

- **Location:** `<workspace>/.cache/snapshots/<site_slug>/` — `pages/<key>.json`
  sidecars + gzip raw bodies in `raw/`, plus `_manifest.json` (the last full
  snapshot, served by the manifest endpoints with no crawl).
- **Conditional GET:** ETag / Last-Modified are stored verbatim and replayed as
  `If-None-Match` / `If-Modified-Since`. A `304` reuses the cached body.
- **Content hashing:** when a server omits validators, a SHA-256 of the body
  detects unchanged pages anyway. (This hash matches `ContentParser._hash_content`,
  so the snapshot and the audit pipeline agree.)
- **Stale-on-error:** if a live fetch fails on a re-run, the previous cached body
  is served and flagged `stale`; the snapshot is marked `degraded` if too many
  pages are stale, so an outage never silently shrinks a backup.
- **Flags:** `--refresh` ignores validators and re-fetches; `--no-cache` purges
  and rebuilds; `--ttl N` skips revalidation for entries younger than `N` seconds.

## Discovery (Jekyll-tuned)

1. `robots.txt` — for the `Sitemap:` declaration, crawl rules (honored by
   default; `--no-robots` to ignore), and `Crawl-delay`.
2. `sitemap.xml` — handles `<urlset>` and nested `<sitemapindex>`. Primary source.
3. `feed.xml` / `atom.xml` — fallback / recent-posts augmenter.
4. Same-domain link BFS — always runs as a safety net (bounded by a separate
   `--max-link-pages` budget so it can't starve sitemap pages).

URLs are normalized for stable cache identity (fragment dropped, scheme/host
lowercased, default port and `index.html` stripped, duplicate slashes collapsed).
Off-host links are recorded but not crawled unless `--include-external`.
Pagination/tag/date-archive traps are skipped by default.

## Safety

- **SSRF:** every request (including each redirect hop, which are followed
  manually) is gated by a host guard that resolves the target via
  `getaddrinfo` and rejects loopback/private/link-local/reserved addresses
  (IPv4 **and** IPv6). Set `AIEO_SNAPSHOT_ALLOW_PRIVATE=1` to allow private hosts
  (used by the offline test fixture).
- **Caps:** `--max-pages`, `--max-depth`, and a per-page byte cap bound every crawl.

## Key options

| Option | Default | Meaning |
| --- | --- | --- |
| `--formats` | `json,markdown,html,text` | Comma list of formats |
| `--output` / `-o` | workspace `audits/snapshots/<slug>/<ts>/` | Output directory |
| `--max-pages` | 500 | Hard page cap |
| `--max-depth` | 6 | Link-following depth cap |
| `--delay` | 0.25 | Polite seconds between live fetches (robots `Crawl-delay` can raise it) |
| `--refresh` | off | Ignore cache validators; re-fetch all |
| `--no-cache` | off | Purge the site cache and rebuild |
| `--no-robots` | off | Ignore robots.txt |
| `--include-external` | off | Also crawl off-host links |
| `--include-assets` | off | Download + inline images for a fully offline HTML/bundle |

## Tests

`backend/tests/test_site_snapshot.py` runs fully offline (a fixture Jekyll site
served from `127.0.0.1` by `http.server`), with no network egress and no API
key — covering discovery, robots, incremental 304 caching, stale-on-error, hash
parity, every exporter, the stdlib PDF's structural validity, and the SSRF guard.
