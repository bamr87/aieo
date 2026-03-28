---
name: temporal_anchoring
display_name: Temporal Anchoring
weight: 10
max_score: 10
---

## What to Evaluate

Check whether the content includes dates, version numbers, and freshness signals that help AI engines determine when the information is current and relevant. AI engines strongly prefer temporally anchored content because they need to assess information freshness.

## Scoring Criteria

- **Explicit dates** (0-4 points): Publication dates, "as of [date]", "updated [date]", event dates. Must be meaningful dates related to the content (not incidental numbers like phone numbers or zip codes).
- **Version/edition markers** (0-3 points): Software versions ("v2.1", "React 18"), standard editions ("2024 edition"), methodology versions.
- **Freshness signals** (0-3 points): "Currently", "as of this writing", "latest", update history, revision dates.

## High Score Examples

- "This guide was last updated on March 15, 2025, and covers Python 3.12."
- "As of Q4 2024, the market has shifted toward..."
- Content with a visible "Last updated: [date]" header

## Low Score Indicators

- No dates anywhere in the content
- Only incidental numbers (phone numbers, prices) that look like years
- "Recently" or "soon" without specific timeframes

## Context Sensitivity

- Evergreen content (e.g., "What is photosynthesis?") needs fewer temporal anchors but still benefits from "as of [year]"
- News/trends content MUST have strong temporal anchoring to score well
- Product pages should reference current pricing dates, version numbers
- Don't count dates in copyright footers or boilerplate as meaningful temporal anchors
