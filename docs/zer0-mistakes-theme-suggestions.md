# Structural / theme suggestions for zer0-mistakes

These recommendations come from crawling a live zer0-mistakes site
(bashconsultants.com, 44 pages) with the AIEO **site snapshot** tool and
analyzing the rendered HTML. They reduce duplicated chrome in any
crawl/extraction **and** improve accessibility and AI-engine citability (which
is AIEO's whole purpose: semantic structure + schema = better AI extraction).

## What the crawl found

| Signal | Result |
| --- | --- |
| Repeated chrome (nav/sidebar/footer/cookie/TOC) | **~56% of total word count** was the same boilerplate copied onto every page |
| `<main>` landmark | Present on the **page/post** layout, **missing** on the **home/landing** layout (falls back to `<div id="main-content">`) |
| `<h1>` per page | 1 on `/about/` ✓ — but **10 on the home page** ✗ |
| `<article>` | 0 — posts use `.h-entry` divs, never the `<article>` element |
| `<section>` | 0 — hero/feature/CTA blocks are bare `<div>`s |
| JSON-LD, `<time>`, microformats | Present on page/post ✓, absent on home/landing ✗ |
| `<meta name="description">` | Per-page on `/about/` ✓; generic on home (`"Modern day IT Solutions"`) |

The standard layout is in good shape. **Almost every issue is in the
home/landing/splash layout(s)** plus a few global chrome items.

The AIEO crawler now strips this chrome automatically (main-content extraction),
but fixing it at the theme level helps *every* consumer — search engines, AI
engines, screen readers, reader-mode, and any scraper — not just AIEO.

---

## 1. Use a single `<main id="main-content">` in **every** layout (highest impact)

The home/landing layout renders content in `<div id="main-content">`. Every other
consumer looks for the `<main>` landmark; without it, extractors fall back to the
whole `<body>` and drag in nav/footer/modals.

```html
<!-- _layouts/default.html (or home.html / splash.html) -->
<!-- before -->
<div id="main-content">
  {{ content }}
</div>

<!-- after -->
<main id="main-content" role="main">
  {{ content }}
</main>
```

There must be exactly **one** `<main>` per page. This single change is what
moves the home/landing pages from "whole body, chrome included" to "clean
content."

## 2. Exactly one `<h1>` per page

The home page emits **10 `<h1>` elements** (brand, hero, every feature card…).
That is an SEO/accessibility/AI antipattern — `<h1>` should name *the page*.

```html
<!-- Hero: the ONE h1 -->
<section class="hero" aria-labelledby="page-title">
  <h1 id="page-title">{{ page.title | default: site.title }}</h1>
  …
</section>

<!-- Feature cards / sections: demote to h2/h3 -->
<section aria-labelledby="services-h">
  <h2 id="services-h">What we do</h2>
  …
</section>
```

Audit the navbar brand and feature partials — anything that is currently `<h1>`
and isn't the page title should become `<h2>`/`<h3>`.

## 3. Wrap posts in `<article>` (with the microformats/schema you already emit)

The post layout already adds `.h-entry`/`.e-content` and JSON-LD — just promote
the wrapper to the semantic element so crawlers and AI key on it:

```html
<!-- _layouts/post.html -->
<main id="main-content" role="main">
  <article class="h-entry" itemscope itemtype="https://schema.org/Article">
    <header>
      <h1 class="p-name" itemprop="headline">{{ page.title }}</h1>
      <p class="byline">
        by <span class="p-author" itemprop="author">{{ page.author | default: site.author.name }}</span>
        on <time class="dt-published" itemprop="datePublished"
                 datetime="{{ page.date | date_to_xmlschema }}">{{ page.date | date: "%B %-d, %Y" }}</time>
      </p>
    </header>
    <div class="e-content" itemprop="articleBody">
      {{ content }}
    </div>
  </article>
</main>
```

## 4. Bring `<section>` semantics + schema to the home/landing layout

Hero, feature grid, and CTA blocks are bare `<div>`s. Wrap each in a
`<section>` with an `aria-labelledby` pointing at its heading. Add
`Organization`/`WebSite` JSON-LD on the home page (the page/post layout already
emits `Article`):

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "{{ site.title }}",
  "url": "{{ site.url }}",
  "logo": "{{ '/assets/brand/favicon.svg' | absolute_url }}",
  "description": "{{ page.description | default: site.description }}"
}
</script>
```

## 5. Mark the in-page Table of Contents as navigation

The TOC appears inside the content on ~half the pages. Wrap it so it's
recognized as navigation (and excluded from content extraction / reader mode):

```html
<nav class="toc" aria-label="Table of contents">
  {{ toc_html }}
</nav>
```

## 6. Keep dialogs / offcanvas / cookie UI out of the content flow

The search modal, shortcuts modal, info offcanvas (~800 chars), and cookie
settings modal (~1300 chars) are siblings of the content and pollute naive
extraction. They already have some roles — make the default state explicit:

```html
<div id="cookieSettingsModal" class="modal fade" role="dialog"
     aria-modal="true" aria-hidden="true" hidden inert> … </div>
```

`aria-hidden="true"` + `hidden`/`inert` while closed tells every extractor and
assistive tech to skip them, and they should render near the end of `<body>`.

## 7. Per-page `<meta name="description">`

The home page's description is the generic tagline. A specific per-page
description improves AI snippets, search results, and the snapshot's per-page
summary:

```liquid
<meta name="description"
      content="{{ page.description | default: page.excerpt | default: site.description | strip_html | truncate: 160 }}">
```

## 8. (Optional) Emit `/llms.txt`

A small, plain-text index of the site's key pages for LLMs is becoming a
convention and fits zer0-mistakes' AI-friendly goals. A Jekyll page that loops
`site.pages`/`site.posts` and lists `title + url + description` is enough.

---

## Why this matters three ways

- **Cleaner backups/exports**: removes the ~56% chrome duplication from any crawl.
- **Accessibility**: one `<h1>`, real landmarks (`<main>`/`<nav>`/`<article>`),
  and `inert` dialogs are direct WCAG wins.
- **AI Engine Optimization**: `<main>`/`<article>` + schema.org + clean content
  boundaries are exactly what ChatGPT/Claude/Gemini/Perplexity use to extract
  and cite content — the thing AIEO scores for.

A focused pass on the home/landing/splash layout(s) (items 1–4) captures most of
the value; items 5–8 are global polish.
