---
name: prd
display_name: PRD Lineage
inputs: repo_root
outputs: json
model_hint: gpt-5.4
---
Search a product repository, identify every PRD element and lineage witness (README, CHANGELOG, agent instructions, docs, packaging), then return completeness, drift, and alignment actions.

Do not invent product facts. Preserve original intent. Label hypotheses. Every improvement must make the spec more buildable or the lineage more consistent.

Return JSON with: product_name, canonical_prd, maturity, completeness, drift, lineage, prd_improvements, alignment_actions, open_questions, context_brief.
