"""Filesystem-backed content workspace service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


WORKSPACE_DIRS = [
    "context",
    "topics",
    "research",
    "drafts",
    "rewrites",
    "review-required",
    "published",
    "landing-pages",
    "audits",
    "config",
    ".cache",
]


CONTEXT_TEMPLATES: Dict[str, str] = {
    "context/brand-voice.md": "# Brand Voice\n\n## Voice pillars\n\n- \n\n## Tone guidance\n\n- \n\n## Core messages\n\n- \n",
    "context/style-guide.md": "# Style Guide\n\n## Grammar and mechanics\n\n- \n\n## Formatting conventions\n\n- \n",
    "context/writing-examples.md": "# Writing Examples\n\n## Example 1\n\n- URL:\n- Why it works:\n\n## Example 2\n\n- URL:\n- Why it works:\n",
    "context/target-keywords.md": "# Target Keywords\n\n## Topic clusters\n\n### Cluster\n\n- Pillar keyword:\n- Long-tail variations:\n- Intent:\n",
    "context/internal-links-map.md": "# Internal Links Map\n\n## Key pages\n\n- URL:\n- Recommended anchors:\n",
    "context/competitor-analysis.md": "# Competitor Analysis\n\n## Primary competitors\n\n- \n\n## Content gaps\n\n- \n",
    "context/seo-guidelines.md": "# SEO Guidelines\n\n## Required checks\n\n- Word count:\n- Keyword usage:\n- Link strategy:\n- Meta constraints:\n",
    "context/cro-best-practices.md": "# CRO Best Practices\n\n## Above-the-fold\n\n- \n\n## CTA\n\n- \n",
    "context/features.md": "# Product Features\n\n## Core features\n\n- Feature:\n- Benefit:\n",
    "config/competitors.json": '{\n  "competitors": [],\n  "keywords": []\n}\n',
}


@dataclass
class WorkspaceNode:
    path: str
    type: str


class WorkspaceService:
    """Manage the AIEO markdown workspace rooted at a configured directory."""

    def __init__(self, root: Path):
        self.root = root

    def initialize(self) -> Dict[str, str]:
        self.root.mkdir(parents=True, exist_ok=True)
        for dname in WORKSPACE_DIRS:
            (self.root / dname).mkdir(parents=True, exist_ok=True)
        for rel_path, contents in CONTEXT_TEMPLATES.items():
            target = self.root / rel_path
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding="utf-8")
        return {"workspace_root": str(self.root)}

    def _resolve(self, rel_path: str) -> Path:
        clean = rel_path.lstrip("/")
        root = self.root.resolve()
        full = (root / clean).resolve()
        # Use path-component containment (not str.startswith, which would accept
        # a sibling directory sharing the root's name prefix, e.g. "<root>-evil").
        if full != root and not full.is_relative_to(root):
            raise ValueError("Path escapes workspace root")
        return full

    def list_tree(self) -> List[WorkspaceNode]:
        nodes: List[WorkspaceNode] = []
        for path in sorted(self.root.rglob("*")):
            rel = path.relative_to(self.root).as_posix()
            nodes.append(
                WorkspaceNode(path=rel, type="dir" if path.is_dir() else "file")
            )
        return nodes

    def read_file(self, rel_path: str) -> Dict[str, str]:
        path = self._resolve(rel_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(rel_path)
        return {"path": rel_path, "content": path.read_text(encoding="utf-8")}

    def write_file(self, rel_path: str, content: str) -> Dict[str, str]:
        path = self._resolve(rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": rel_path}

    def move_file(self, source_path: str, dest_path: str) -> Dict[str, str]:
        src = self._resolve(source_path)
        dst = self._resolve(dest_path)
        if not src.exists():
            raise FileNotFoundError(source_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        return {"source": source_path, "destination": dest_path}
