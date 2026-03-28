---
name: entity_density
display_name: Entity Density
weight: 15
max_score: 15
---

## What to Evaluate

Measure the density of named entities — specific people, organizations, products, locations, dates, and technical terms — that make content uniquely identifiable and citable by AI engines. AI engines cite content with high entity specificity because it provides concrete, verifiable facts.

## Scoring Criteria

- **Named people/organizations** (0-5 points): Specific names (e.g., "Marie Curie", "Anthropic", "Sopris Accounting") vs. generic references ("a company", "researchers")
- **Products/technologies** (0-5 points): Specific product names, versions, standards (e.g., "GPT-4", "TLS 1.3", "React 18") vs. vague references ("the latest version")
- **Locations and dates** (0-5 points): Specific geographic references and temporal markers that ground the content in reality

## Target Density

- Excellent: 3+ unique entities per 100 words
- Good: 1.5-3 unique entities per 100 words
- Weak: <1 entity per 100 words

## High Score Examples

- "Anthropic released Claude 3.5 Sonnet in June 2024, achieving state-of-the-art performance on the MMLU benchmark with 88.7% accuracy."
- "Located in Carbondale, Colorado, Sopris Accounting serves small businesses across the Roaring Fork Valley."

## Low Score Indicators

- "Our company provides great services to customers in the area." (zero entities)
- "The product was updated recently with new features." (no specifics)

## Context Sensitivity

- Service/about pages SHOULD be entity-rich (who, where, what specifically)
- Opinion pieces may naturally have fewer entities — score relative to content type
- Don't count boilerplate navigation entities (menu items, footer links)
