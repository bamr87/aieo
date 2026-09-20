"""Phase 2 — extract PRD-element facts from mapped sources (no judgement)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .config import PrdConfig
from .elements import ELEMENTS
from .model import LineageEdge, PrdInventory, SourceNode

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_VERSION_RE = re.compile(
    r"(?i)version[^0-9]{0,12}v?(\d+\.\d+(?:\.\d+)?)|"
    r"\bv(\d+\.\d+(?:\.\d+)?)\b|"
    r"\[(\d+\.\d+(?:\.\d+)?)\]"
)
_TOML_NAME_RE = re.compile(r'(?m)^\s*name\s*=\s*["\']([^"\']+)["\']')
_TOML_VERSION_RE = re.compile(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']')


def extract_all(inv: PrdInventory, root: Path, cfg: Optional[PrdConfig] = None) -> Dict[str, int]:
    cfg = cfg or PrdConfig()
    root = root.resolve()
    extracted = failed = 0
    known_paths = {s.path for s in inv.sources}
    for src in inv.sources:
        try:
            text = _read(root / src.path, cfg)
            _fill(src, text, cfg)
            extracted += 1
        except Exception as exc:
            src.error = str(exc)
            failed += 1
        for target in src.outbound:
            if target in known_paths:
                inv.edges.append(LineageEdge(source=src.path, target=target))
    inv.element_index = _index(inv.sources)
    return {"extracted": extracted, "failed": failed}


def _read(path: Path, cfg: PrdConfig) -> str:
    data = path.read_bytes()
    if b"\x00" in data[:1024]:
        raise ValueError("binary file")
    return data.decode("utf-8", errors="replace")[: cfg.max_text_chars]


def _fill(src: SourceNode, text: str, cfg: PrdConfig) -> None:
    src.extracted = True
    src.word_count = len(text.split())
    src.headings = [h.strip() for _, h in _HEADING_RE.findall(text)]
    src.title = src.headings[0] if src.headings else None
    src.excerpt = text[: min(len(text), cfg.agent_max_chars)]
    src.outbound = _repo_links(text, src.path)
    src.element_hits = match_elements(text, src.headings)
    src.product_name, src.version = _identity(src, text)


def match_elements(text: str, headings: Iterable[str]) -> List[str]:
    blob = " ".join(headings).lower()
    body = text.lower()
    hits: List[str] = []
    for el in ELEMENTS:
        heading_hit = any(alias in blob for alias in el.heading_aliases)
        body_hit = any(sig in body for sig in el.body_signals) or heading_hit
        if heading_hit or body_hit:
            hits.append(el.id)
    return hits


def _repo_links(text: str, source_path: str) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    source_dir = str(Path(source_path).parent)
    for _, href in _LINK_RE.findall(text):
        target = _normalize_href(href, source_dir)
        if not target or target in seen:
            continue
        seen.add(target)
        out.append(target)
    return out


def _normalize_href(href: str, source_dir: str) -> Optional[str]:
    href = href.strip().split("#", 1)[0].strip()
    if not href or href.startswith(("http://", "https://", "mailto:", "data:")):
        return None
    if href.startswith("/"):
        return href.lstrip("/")
    combined = str(Path(source_dir) / href) if source_dir not in (".", "") else href
    parts: List[str] = []
    for part in combined.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts) or None


def _identity(src: SourceNode, text: str) -> Tuple[Optional[str], Optional[str]]:
    name = _name_from_title(src.title)
    version = _first_version(text)
    lower = Path(src.path).name.lower()
    if lower == "package.json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            name = data.get("name") or name
            version = data.get("version") or version
    elif lower in ("pyproject.toml", "cargo.toml"):
        match_n = _TOML_NAME_RE.search(text)
        match_v = _TOML_VERSION_RE.search(text)
        if match_n:
            name = match_n.group(1)
        if match_v:
            version = match_v.group(1)
    return _clean_name(name), version


def _name_from_title(title: Optional[str]) -> Optional[str]:
    if not title:
        return None
    cleaned = re.sub(r"^(prd|product requirements(?: document)?)\s*[:\-–—]?\s*", "", title, flags=re.I)
    cleaned = re.sub(r"\s*[—|:].*$", "", cleaned).strip()
    return cleaned or title.strip()


def _clean_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    name = name.strip().strip("`\"'")
    return name or None


def _first_version(text: str) -> Optional[str]:
    match = _VERSION_RE.search(text[:4000])
    if not match:
        return None
    return next((g for g in match.groups() if g), None)


def _index(sources: List[SourceNode]) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for src in sources:
        for el in src.element_hits:
            index.setdefault(el, []).append(src.path)
    return index
