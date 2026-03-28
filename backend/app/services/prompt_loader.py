"""Prompt loader for AIEO scoring engine.

Loads and assembles prompt files from the prompts/ directory.
Pattern definitions, scoring rubrics, and system instructions
are all defined in external markdown files — not hardcoded in Python.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional


# Default prompts directory relative to this file
DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class PromptLoader:
    """Load and assemble AIEO prompt files."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir else DEFAULT_PROMPTS_DIR
        self._cache: Dict[str, str] = {}
        self._patterns_cache: Optional[List[Dict]] = None

    def load_system_prompt(self) -> str:
        """Load the system prompt that defines the AI's role."""
        return self._read_file(self.prompts_dir / "system.md")

    def load_rubric(self) -> str:
        """Load the scoring rubric (output format and rules)."""
        return self._read_file(self.prompts_dir / "scoring_rubric.md")

    def load_patterns(self) -> List[Dict]:
        """Load all pattern definitions from prompts/patterns/*.md.

        Returns list of dicts with keys: name, display_name, weight, max_score, body
        """
        if self._patterns_cache is not None:
            return self._patterns_cache

        patterns_dir = self.prompts_dir / "patterns"
        if not patterns_dir.exists():
            return []

        patterns = []
        for md_file in sorted(patterns_dir.glob("*.md")):
            raw = self._read_file(md_file)
            frontmatter, body = self._parse_frontmatter(raw)
            patterns.append({
                "name": frontmatter.get("name", md_file.stem),
                "display_name": frontmatter.get("display_name", md_file.stem.replace("_", " ").title()),
                "weight": int(frontmatter.get("weight", 10)),
                "max_score": int(frontmatter.get("max_score", 10)),
                "body": body.strip(),
            })

        self._patterns_cache = patterns
        return patterns

    def build_evaluation_prompt(self, content_summary: Dict) -> str:
        """Build the full evaluation prompt sent to the AI model.

        Args:
            content_summary: Dict with keys like text, headers, tables, lists, links, word_count
        """
        rubric = self.load_rubric()
        patterns = self.load_patterns()

        # Build content summary section
        content_section = self._format_content_summary(content_summary)

        # Build pattern definitions section
        pattern_section = self._format_pattern_definitions(patterns)

        prompt = f"""## Content to Evaluate

{content_section}

## Scoring Rubric

{rubric}

## Pattern Definitions

{pattern_section}

## Instructions

Evaluate the content above against EACH pattern listed. Return your analysis as the JSON structure defined in the Scoring Rubric. Every pattern must appear in your response — score 0 if not applicable to this content type.

Evaluate contextually: consider what type of content this is and what patterns are appropriate for it. A personal blog post is scored differently from technical documentation."""

        return prompt

    def get_pattern_names(self) -> List[str]:
        """Return list of pattern names."""
        return [p["name"] for p in self.load_patterns()]

    def get_total_max_score(self) -> int:
        """Return sum of all pattern weights (used for normalization)."""
        return sum(p["weight"] for p in self.load_patterns())

    def _format_content_summary(self, parsed: Dict) -> str:
        """Format parsed content into a readable summary for the AI."""
        sections = []

        # Basic stats
        sections.append(f"**Word count:** {parsed.get('word_count', 0)}")
        sections.append(f"**Character count:** {parsed.get('char_count', 0)}")

        # Headers
        headers = parsed.get("headers", [])
        if headers:
            header_list = "\n".join(
                f"  - {'#' * h['level']} {h['text']}" for h in headers[:30]
            )
            sections.append(f"**Headers ({len(headers)}):**\n{header_list}")
        else:
            sections.append("**Headers:** None")

        # Tables
        tables = parsed.get("tables", [])
        if tables:
            table_info = []
            for i, t in enumerate(tables[:10]):
                table_info.append(f"  - Table {i+1}: {t.get('row_count', 0)} rows × {t.get('column_count', 0)} columns")
                if t.get("rows"):
                    header_row = " | ".join(str(c) for c in t["rows"][0][:5])
                    table_info.append(f"    Headers: {header_row}")
            sections.append(f"**Tables ({len(tables)}):**\n" + "\n".join(table_info))
        else:
            sections.append("**Tables:** None")

        # Lists
        lists = parsed.get("lists", [])
        if lists:
            list_info = "\n".join(
                f"  - {l['type']} list: {l.get('item_count', 0)} items"
                for l in lists[:10]
            )
            sections.append(f"**Lists ({len(lists)}):**\n{list_info}")
        else:
            sections.append("**Lists:** None")

        # Links
        links = parsed.get("links", [])
        external_links = [l for l in links if l.get("url", "").startswith(("http://", "https://"))]
        sections.append(f"**Links:** {len(links)} total, {len(external_links)} external")

        # Full text (truncated for large content)
        text = parsed.get("text", "")
        if len(text) > 12000:
            sections.append(f"**Content text (truncated to 12000 chars):**\n\n{text[:12000]}...")
        else:
            sections.append(f"**Content text:**\n\n{text}")

        return "\n\n".join(sections)

    def _format_pattern_definitions(self, patterns: List[Dict]) -> str:
        """Format pattern definitions into a single prompt section."""
        sections = []
        for p in patterns:
            sections.append(
                f"### {p['display_name']} (name: `{p['name']}`, weight: {p['weight']}, max: {p['max_score']})\n\n{p['body']}"
            )
        return "\n\n---\n\n".join(sections)

    def _read_file(self, path: Path) -> str:
        """Read a file with caching."""
        key = str(path)
        if key not in self._cache:
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found: {path}")
            self._cache[key] = path.read_text(encoding="utf-8")
        return self._cache[key]

    def _parse_frontmatter(self, text: str) -> tuple:
        """Parse YAML-like frontmatter from a markdown file.

        Returns (frontmatter_dict, body_text).
        """
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text

        frontmatter_str = match.group(1)
        body = match.group(2)

        # Simple YAML parsing (key: value per line)
        frontmatter = {}
        for line in frontmatter_str.strip().split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                frontmatter[key.strip()] = value.strip()

        return frontmatter, body
