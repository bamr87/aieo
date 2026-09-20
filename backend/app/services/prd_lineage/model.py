"""In-memory model for a PRD-lineage inventory."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

INVENTORY_VERSION = "1"
TOOL_NAME = "aieo-prd-lineage"
GENERATOR = "AIEO PrdLineageService 1.0"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", (value or "").lower()).strip("-")
    return slug or "repo"


@dataclass
class SourceNode:
    path: str
    role: str = "other"
    bytes: int = 0
    extracted: bool = False
    title: Optional[str] = None
    headings: List[str] = field(default_factory=list)
    element_hits: List[str] = field(default_factory=list)
    outbound: List[str] = field(default_factory=list)
    product_name: Optional[str] = None
    version: Optional[str] = None
    word_count: int = 0
    excerpt: str = ""
    error: Optional[str] = None
    analysis: Dict[str, Any] = field(default_factory=dict)
    analysis_method: str = "skipped"
    analysis_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceNode":
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class LineageEdge:
    source: str
    target: str
    kind: str = "markdown_link"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PrdInventory:
    repo_root: str
    repo_slug: str = ""
    created_at: str = ""
    completed_at: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    sources: List[SourceNode] = field(default_factory=list)
    edges: List[LineageEdge] = field(default_factory=list)
    element_index: Dict[str, List[str]] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    phases: Dict[str, Any] = field(default_factory=dict)
    analysis: Dict[str, Any] = field(default_factory=dict)
    analysis_method: str = "skipped"
    degraded: bool = False
    version: str = INVENTORY_VERSION
    generator: str = GENERATOR
    tool: str = TOOL_NAME

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["sources"] = [s.to_dict() for s in self.sources]
        data["edges"] = [e.to_dict() for e in self.edges]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrdInventory":
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        kwargs["sources"] = [SourceNode.from_dict(s) for s in data.get("sources") or []]
        kwargs["edges"] = [
            LineageEdge(**e) if isinstance(e, dict) else e
            for e in data.get("edges") or []
        ]
        return cls(**kwargs)

    @property
    def canonical(self) -> Optional[SourceNode]:
        for src in self.sources:
            if src.role == "canonical_prd":
                return src
        return None
