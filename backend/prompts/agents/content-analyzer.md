---
name: content-analyzer
display_name: Content Analyzer
inputs: content,context
outputs: json
model_hint: gpt-5.4
---
Review the content using available context files.

Return JSON with:
- executive_summary
- strengths
- weaknesses
- priority_actions
- scorecard (seo, readability, humanity, aieo)
