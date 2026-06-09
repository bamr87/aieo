---
name: scrub
display_name: AI Pattern Scrubber
inputs: content
outputs: markdown
model_hint: gpt-5.4
---
Rewrite the content to reduce robotic patterns:
- avoid repetitive sentence openings
- remove filler phrases
- replace excessive em-dashes
- keep facts and structure intact
Return only revised markdown.
