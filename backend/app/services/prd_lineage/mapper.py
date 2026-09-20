"""Phase 1 — walk a product repo and classify PRD-bearing sources."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Set

from .config import MANIFEST_NAMES, SKIP_FILE_NAMES, SKIP_SUFFIXES, TEXT_SUFFIXES, PrdConfig
from .model import SourceNode

_SECRET_PARTS = ("secret", "credential", "id_rsa", "private-key", "private_key")

_ROLE_NAMES = {
    "changelog.md": "changelog",
    "history.md": "changelog",
    "news.md": "changelog",
    "claude.md": "agent_instructions",
    "agents.md": "agent_instructions",
    "contributing.md": "contributing",
    "install.md": "install",
    "installation.md": "install",
}


def map_repo(root: Path, cfg: Optional[PrdConfig] = None) -> List[SourceNode]:
    cfg = cfg or PrdConfig()
    root = root.resolve()
    skip_dirs: Set[str] = set(cfg.skip_dir_names)
    sources: List[SourceNode] = []
    for path in _walk(root, skip_dirs):
        if len(sources) >= cfg.max_files:
            break
        if not _include(path):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > cfg.max_bytes_per_file:
            continue
        rel = path.relative_to(root).as_posix()
        sources.append(SourceNode(path=rel, role=classify(rel), bytes=size))
    sources.sort(key=lambda s: (_role_rank(s.role), s.path.lower()))
    return sources


def classify(rel: str) -> str:
    posix = rel.replace("\\", "/")
    parts = posix.split("/")
    name = parts[-1].lower()
    stem = Path(name).stem.lower()

    if ".prompts" in parts or "prompt" in stem:
        return "prompt_spec"
    if "prompts" in parts and name.endswith(".md"):
        return "prompt_spec"
    if _is_canonical_prd(stem, name):
        return "canonical_prd"
    if name.startswith("readme"):
        return "readme"
    if name in _ROLE_NAMES:
        return _ROLE_NAMES[name]
    if name in ("copilot-instructions.md",) or stem == ".cursorrules":
        return "agent_instructions"
    if name in MANIFEST_NAMES or name.endswith(".gemspec"):
        return "packaging"
    if name.startswith("openapi") or name.startswith("swagger"):
        return "api"
    if "issue_template" in posix.lower() or "issue-template" in posix.lower():
        return "issue_template"
    if len(parts) >= 2 and parts[0] == "docs":
        if stem in ("architecture", "adr"):
            return "architecture"
        if stem == "api":
            return "api"
        if stem in ("cli", "install", "installation"):
            return "install" if stem != "cli" else "docs"
        return "docs"
    if stem == "architecture":
        return "architecture"
    return "other"


def _is_canonical_prd(stem: str, name: str) -> bool:
    if name in ("prd.md", "prd.markdown", "prd.rst", "prd.txt"):
        return True
    if stem in ("product", "product-requirements", "product_requirements"):
        return True
    return stem.startswith("prd-")


def _include(path: Path) -> bool:
    name = path.name
    lower = name.lower()
    if lower in SKIP_FILE_NAMES:
        return False
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    if any(part in lower for part in _SECRET_PARTS):
        return False
    if lower in MANIFEST_NAMES or lower.endswith(".gemspec"):
        return True
    if lower.startswith("openapi") or lower.startswith("swagger"):
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def _walk(root: Path, skip_dirs: Set[str]) -> Iterable[Path]:
    for dirpath, dirnames, filenames in _os_walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.endswith(".egg-info")]
        base = Path(dirpath)
        for filename in filenames:
            yield base / filename


def _os_walk(root: Path):
    import os

    return os.walk(root, followlinks=False)


def _role_rank(role: str) -> int:
    order = {
        "canonical_prd": 0,
        "readme": 1,
        "changelog": 2,
        "agent_instructions": 3,
        "architecture": 4,
        "api": 5,
        "install": 6,
        "contributing": 7,
        "packaging": 8,
        "docs": 9,
        "issue_template": 10,
        "prompt_spec": 11,
        "other": 12,
    }
    return order.get(role, 20)
