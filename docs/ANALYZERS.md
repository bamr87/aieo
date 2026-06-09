# Analyzer Modules

Analyzer modules live in `backend/app/analyzers/` and are consumed by `ScoringEngine`.

## Core analyzers

- `readability_scorer.py`
- `keyword_analyzer.py`
- `search_intent_analyzer.py`
- `content_length_comparator.py`
- `seo_quality_rater.py`
- `content_scorer.py`
- `opportunity_scorer.py`
- `engagement_analyzer.py`
- `competitor_gap_analyzer.py`

## CRO analyzers

- `above_fold_analyzer.py`
- `cta_analyzer.py`
- `trust_signal_analyzer.py`
- `landing_page_scorer.py`
- `cro_checker.py`

`ScoringEngine.score()` now returns `dimensions` plus detailed keys:

- `seo_quality`
- `readability`
- `search_intent`
- `keyword_analysis`
- `serp_comparison`
- `humanity`
- `cro`
