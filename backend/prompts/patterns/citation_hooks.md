---
name: citation_hooks
display_name: Citation Hooks
weight: 10
max_score: 10
---

## What to Evaluate

Identify explicit source attributions, evidence markers, and credibility signals that make AI engines confident enough to cite the content. Content with clear attribution chains is preferentially cited because AIs can verify and attribute claims.

## Scoring Criteria

- **Source attributions** (0-4 points): Phrases like "according to [source]", "research from [institution]", "published in [journal]", "[Expert name] states". Award more for specific, verifiable attributions.
- **Evidence markers** (0-3 points): Data points, statistics, study references, methodology descriptions that signal factual rigor.
- **External references** (0-3 points): Links to authoritative sources, bibliographies, footnotes, "Sources:" sections.

## High Score Examples

- "According to a 2024 Gartner report, 65% of enterprises will adopt AI-native tools by 2026."
- "Dr. Sarah Chen, Director of AI Research at Stanford, explains that..."
- Content with a "Sources" or "References" section with real, verifiable links

## Low Score Indicators

- Unsourced claims: "Studies show that..." (which studies?)
- No external links or references
- All claims are opinion without evidence markers

## Context Sensitivity

- Personal blogs sharing experiences don't need heavy citations — score relative to claims made
- Technical documentation should cite standards, RFCs, or official docs
- Marketing claims about "best" or "leading" should be supported with evidence
- Distinguish real citations from fake "according to experts" padding
