# AIEO CLI Documentation

## Installation

### CLI (requires running backend API)

```bash
cd cli
pip install -r requirements.txt
pip install -e .
```

### Standalone Batch Audit (no backend required)

The standalone batch audit script (`run_audit.py`) uses the scoring engine directly, bypassing the need for the full API stack (PostgreSQL, Redis, etc.). It only requires lightweight Python dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install httpx beautifulsoup4 markdown html2text
```

For improved entity density scoring, optionally install spaCy:

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

> **Note:** Without spaCy, entity density scoring will return 0 for all sites. All other 9 patterns score normally.

## Usage

### Audit Content

```bash
# Audit a URL
aieo audit https://example.com/article

# Audit a local file
aieo audit --file article.md
aieo audit article.md

# Output as JSON
aieo audit article.md --json

# Set API key
export AIEO_API_KEY=your-api-key
aieo audit article.md
```

> **Note:** The `aieo audit` CLI command requires the backend API to be running. For quick audits without the full stack, use the standalone batch script below.

### Batch Audit (Standalone)

Audit multiple URLs from `sites.txt` without running the backend:

```bash
python run_audit.py
```

This reads URLs from `sites.txt` (one URL per line), fetches each site's HTML, runs the scoring engine, and saves results to a temporary directory.

**Input format** (`sites.txt`):
```
https://example.com/
https://another-site.com/page
```

**Output:**
- One JSON file per site in a temp directory (e.g., `/tmp/aieo_results_XXXXX/`)
- A `summary.json` with consolidated results
- Console output with a summary table:

```
================================================================================
AIEO AUDIT SUMMARY
================================================================================
URL                                            Score  Grade   Words  Gaps
--------------------------------------------------------------------------------
https://example.com/                            42.0      F     725     6
https://another-site.com/page                   21.5      F    1760     4
================================================================================
```

**Per-site JSON output includes:**
- `score` (0-100) and `grade` (A+ through F)
- `word_count` of parsed content
- `pattern_scores` — detailed breakdown for all 10 AIEO patterns
- `gaps` — prioritized list of missing patterns with severity
- `anti_pattern_penalties` — points deducted for anti-patterns

### Optimize Content

```bash
# Optimize a file
aieo optimize article.md

# Save to output file
aieo optimize article.md --output optimized.md

# Show diff
aieo optimize article.md --diff

# Aggressive optimization
aieo optimize article.md --style aggressive
```

### Dashboard

```bash
# View dashboard
aieo dashboard

# JSON output
aieo dashboard --json
```

## Configuration

Set environment variables:

- `AIEO_API_KEY`: Your API key
- `AIEO_API_URL`: API base URL (default: http://localhost:8000/api/v1)

## Scoring

The scoring engine evaluates content against 10 AIEO patterns with the following weights:

| Pattern | Weight | Description |
|---------|-------:|-------------|
| Structured Data | 20 | Tables, lists, headers per 500 words |
| Comparison Tables | 15 | Side-by-side comparisons + keywords |
| Recursive Depth | 15 | Nested Q&A, follow-up questions |
| Entity Density | 15 | Named entities per 100 words (requires spaCy) |
| FAQ Injection | 15 | FAQ sections and question headers |
| Temporal Anchoring | 10 | Dates, versions, freshness indicators |
| Citation Hooks | 10 | Source attributions ("according to", links) |
| Definitional Precision | 10 | Explicit definitions ("is defined as") |
| Meta-Context | 10 | Importance explanations ("this matters because") |
| Procedural Clarity | 5 | Step-by-step numbered procedures |

**Grading scale:** A+ (90+), A (80+), B (70+), C (60+), D (50+), F (<50)

**Anti-pattern penalties** (deducted from total):
- Over-optimization: >10 structured elements per 1000 words → −20 points
- Keyword stuffing: any word >5% frequency → −15 points
- Missing structure in long content: >1000 words with no tables or lists → −15 points


