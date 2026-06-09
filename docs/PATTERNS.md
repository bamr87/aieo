# AIEO Pattern Library

## Overview

AIEO patterns are content structures that increase citation likelihood by AI engines. Each pattern has been validated to show measurable citation boost.

## Patterns

### 1. Structured Data (15-25% boost)

Convert prose into tables, lists, and structured formats.

**Before:**
```
X costs $10, Y costs $20, Z costs $15
```

**After:**
```
| Product | Price |
|---------|-------|
| X       | $10   |
| Y       | $20   |
| Z       | $15   |
```

### 2. Entity Density (10-20% boost)

Increase named entities (people, places, products, dates) per paragraph.

**Before:**
```
The tool is good for writing
```

**After:**
```
Anthropic's Claude 3.5 Sonnet (released June 2024) outperforms GPT-4 for long-form writing
```

### 3. Citation Hooks (5-15% boost)

Explicit source attribution.

**Before:**
```
This approach works well
```

**After:**
```
According to research from MIT (2024), this approach improves outcomes by 40%
```

### 4. Recursive Depth (20-30% boost)

Answer questions within questions (nested Q&A format).

**Before:**
```
What is X? X is a tool.
```

**After:**
```
What is X? X is a tool for...

**But how does X compare to Y?** X differs from Y in...
```

### 5. Temporal Anchoring (10-15% boost)

Explicit dates, version numbers, freshness indicators.

**Before:**
```
The API supports webhooks
```

**After:**
```
As of December 2025, API v2.1 supports webhooks with retry logic
```

### 6. Comparison Tables (25-40% boost)

Side-by-side comparisons in tabular format.

**Before:**
```
X is faster but Y is cheaper
```

**After:**
```
| Feature | X | Y | Winner |
|---------|---|---|--------|
| Speed   | Fast | Slow | X |
| Price   | High | Low | Y |
```

### 7. Definitional Precision (8-12% boost)

Explicit definitions.

**Before:**
```
AIEO helps optimize content
```

**After:**
```
**AIEO** (AI Engine Optimization) is defined as the practice of optimizing content for AI engine citation
```

### 8. Step-by-Step Procedures (12-18% boost)

Numbered steps for procedural content.

**Before:**
```
First do this, then do that, finally...
```

**After:**
```
**Step 1:** Configure...
**Step 2:** Deploy...
**Step 3:** Verify...
```

### 9. FAQ Injection (15-25% boost)

Anticipate and answer common questions.

**Before:**
```
Content without questions
```

**After:**
```
## Frequently Asked Questions

### How much does X cost?
X costs $Y per month...
```

### 10. Meta-Context (5-10% boost)

Explain why information matters.

**Before:**
```
Use HTTPS for API calls
```

**After:**
```
Use HTTPS for API calls. **This is critical because** unencrypted traffic exposes...
```

## Pattern Priority

Patterns are prioritized by citation boost:

1. Comparison Tables (25-40%)
2. Recursive Depth (20-30%)
3. Structured Data (15-25%)
4. FAQ Injection (15-25%)
5. Step-by-Step Procedures (12-18%)
6. Entity Density (10-20%)
7. Temporal Anchoring (10-15%)
8. Definitional Precision (8-12%)
9. Citation Hooks (5-15%)
10. Meta-Context (5-10%)

## Scoring Weights

The scoring engine assigns the following point weights (normalized to 100):

| Pattern | Max Points | Weight | Detection Method |
|---------|----------:|-------:|------------------|
| Structured Data | 20 | 20 | Tables + lists + headers per 500 words |
| Comparison Tables | 15 | 15 | Table count + comparison keywords (vs, compare, difference) |
| Recursive Depth | 15 | 15 | Nested questions, follow-up conjunctions |
| Entity Density | 15 | 15 | Unique named entities per 100 words (requires spaCy) |
| FAQ Injection | 15 | 15 | FAQ section keywords + question-mark headers |
| Temporal Anchoring | 10 | 10 | Years, full dates, "as of", version numbers |
| Citation Hooks | 10 | 10 | "According to", "research by", markdown links, "source:" |
| Definitional Precision | 10 | 10 | "Is defined as", "refers to", bold-term definitions |
| Meta-Context | 10 | 10 | "This is important because", "crucially", "essential" |
| Procedural Clarity | 5 | 5 | "Step N", numbered lists, ordinal sequences |

## Anti-Patterns

The scoring engine also detects and penalizes anti-patterns:

| Anti-Pattern | Penalty | Trigger |
|--------------|--------:|---------|
| Over-optimization | −20 | >10 structured elements per 1000 words |
| Keyword stuffing | −15 | Any word (>4 chars) appears >5% of total words |
| Missing structure in long content | −15 | >1000 words with no tables and no lists |

## Multi-Dimension Scoring

AIEO now returns additional dimensions alongside classic pattern scoring:

- `dimensions.aieo` for citation readiness
- `dimensions.seo` for SEO quality
- `dimensions.readability` for readability quality
- `dimensions.humanity` for editorial/human voice quality
- `dimensions.cro` for conversion-oriented landing-page quality

## Entity Density Note

Entity density scoring (Pattern 2) requires spaCy with the `en_core_web_sm` model. Without spaCy installed, this pattern always scores 0, limiting the maximum achievable score. Install with:

```bash
pip install spacy
python -m spacy download en_core_web_sm
```


