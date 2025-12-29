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


