## Output Format

You MUST respond with valid JSON only. No markdown, no explanation outside the JSON.

Return this exact structure:

```json
{
  "patterns": {
    "<pattern_name>": {
      "score": <number>,
      "max": <number>,
      "detected": <boolean>,
      "evidence": ["<specific quote or observation from content>", ...],
      "recommendation": "<one specific, actionable improvement>"
    }
  },
  "anti_patterns": {
    "penalties": <number 0-50>,
    "detected": ["<anti-pattern name>", ...],
    "evidence": ["<specific observation>", ...]
  },
  "content_type": "<detected content type: article, landing_page, documentation, blog_post, product_page, faq, comparison, tutorial, other>",
  "overall_assessment": "<2-3 sentence summary of the content's AIEO strengths and weaknesses>",
  "executive_summary": "<A 3-5 paragraph strategic analysis written for the site owner. Explain what the site does well, what AI engines would struggle to extract, what the biggest missed opportunities are, and how competitors with similar content but better structure would outperform this site in AI citation. Be specific — reference actual content from the page, name specific sections, and explain the 'why' behind each weakness. Write in a consultative, professional tone as if delivering a paid audit report.>",
  "priority_actions": [
    {
      "title": "<Short action title, e.g. 'Add an FAQ section'>",
      "impact": "<high|medium|low>",
      "effort": "<low|medium|high>",
      "description": "<2-3 sentence explanation of what to do, why it matters for AI citation, and what the expected improvement would be. Be specific to THIS site's content.>"
    }
  ],
  "sample_improvements": [
    {
      "section": "<Name of the section or area being improved, e.g. 'Service Description'>",
      "current": "<Direct quote or close paraphrase of existing content>",
      "improved": "<Rewritten version optimized for AIEO patterns. Must be substantive and usable — at least a full paragraph or structured block. Demonstrate how to add definitions, temporal anchoring, structured data, FAQ items, comparison elements, or citation hooks into the actual site content.>",
      "patterns_addressed": ["<pattern_name>", ...]
    }
  ],
  "visual_analysis": {
    "layout_quality": "<1-2 sentence assessment of page layout and visual organization>",
    "visual_hierarchy": "<1-2 sentence assessment of how well the design highlights key content>",
    "readability": "<1-2 sentence assessment of text legibility, contrast, and spacing>",
    "trust_signals": "<1-2 sentence assessment of professional design, branding, authority indicators>",
    "mobile_readiness": "<1-2 sentence assessment of responsive design appearance>",
    "scannability": "<1-2 sentence assessment of how easily key info can be extracted visually>",
    "design_score": <number 0-10>,
    "design_recommendations": ["<specific visual improvement>", ...]
  }
}
```

## Scoring Rules

1. Each pattern score must be between 0 and its `max` value (defined in pattern files).
2. Scores should use 0.5 increments (e.g., 7.5, not 7.3).
3. `detected` is true if the pattern is meaningfully present (not just trace evidence).
4. `evidence` must contain at least 1 item per pattern — quote or paraphrase from the actual content.
5. `recommendation` must be specific to THIS content, not generic advice.
6. Anti-pattern penalties range from 0 (clean content) to 50 (heavily gamed content).
7. `executive_summary` must be 3-5 paragraphs of strategic analysis specific to the site. Reference actual page content, name real sections/elements, and explain the competitive AI citation landscape. Write as a professional consultant delivering an audit.
8. `priority_actions` must contain exactly 3 items, ordered by impact (highest first). Each must be immediately actionable and specific to this site — not generic advice. Include effort level so the site owner can prioritize.
9. `sample_improvements` must contain at least 2 concrete before/after examples. The "current" field should quote or closely paraphrase actual content from the page. The "improved" field must be a complete, usable rewrite — not a description of what to change, but the actual improved text ready to copy-paste. Each improvement should address multiple AIEO patterns simultaneously.
10. `visual_analysis` is REQUIRED when a screenshot is provided, OPTIONAL otherwise. When provided, `design_score` ranges from 0 (unusable) to 10 (exceptional). `design_recommendations` must contain at least 2 specific, actionable visual improvements. All text fields must reference specific elements visible in the screenshot.

## Anti-Patterns to Detect

- **Keyword stuffing**: Same word/phrase repeated at unnatural frequency (>5% of total words)
- **Pattern cramming**: Forced structural elements that don't serve the content (random tables, unnecessary FAQs)
- **Missing structure in long content**: >1000 words with no tables, lists, or sub-headers
- **Over-optimization**: Content reads like it was written for algorithms, not humans
- **Citation fishing**: Fake or unsupported "according to" claims with no real sources
