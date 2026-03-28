---
name: structured_data
display_name: Structured Data
weight: 20
max_score: 20
---

## What to Evaluate

Assess whether the content uses structural elements — tables, lists, and headers — to organize information in ways AI engines can easily parse, extract, and cite.

## Scoring Criteria

- **Tables** (0-8 points): Data tables that organize comparative, factual, or reference data. Award more points for tables with clear column headers, consistent data types, and useful information density.
- **Lists** (0-6 points): Bullet or numbered lists that break down complex information. Award more for lists that enumerate distinct items (features, steps, options) vs. decorative bullets wrapping prose.
- **Headers** (0-6 points): Hierarchical header structure that creates a navigable outline. Award more for descriptive headers that could serve as questions/answers (e.g., "How to Configure SSL" vs. "Section 3").

## High Score Examples

- A product comparison page with a feature matrix table, bulleted requirement lists, and H2/H3 headers for each product
- A how-to guide with step-by-step numbered lists, a prerequisites table, and descriptive section headers

## Low Score Indicators

- Wall of text with no structural elements
- Headers that are vague ("Introduction", "Details", "More Info")
- Only a single flat bullet list in an otherwise unstructured page

## Context Sensitivity

- Personal narratives and essays naturally have less structure — don't penalize below 5 points for these content types
- Technical documentation and comparison pages should score near max to be useful
- Landing pages with minimal text may have high structure-to-text ratio — evaluate proportionally
