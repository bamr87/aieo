"""Persistence for context builds.

HTTP bodies are *not* stored here: they reuse the snapshot crawler's
:class:`~app.services.site_snapshot.snapshot_cache.SnapshotCache`, so a context
build and a site snapshot of the same host share one conditional-GET cache and
neither re-downloads what the other already has. This module only owns the
context *manifests*, which live beside that cache in
``<workspace>/.cache/snapshots/<site_slug>/context/<context_key>.json``.

A site can hold many contexts (one per seed URL), so the manifest name is
derived from the seed path — ``/category/programming`` ->
``category-programming-4f3a1c2b`` — readable, collision-safe and validated
before it is ever joined into a filesystem path.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ..site_snapshot.snapshot_cache import (
    InvalidSlugError,
    SnapshotCache,
    site_slug,
    validate_slug,
)

_KEY_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_MAX_STEM = 48


class InvalidContextKeyError(ValueError):
    """Raised when a context key would escape the context directory."""


def validate_context_key(key: str) -> str:
    if not key or len(key) > 96 or not _KEY_RE.fullmatch(key):
        raise InvalidContextKeyError(f"Invalid context key: {key!r}")
    return key


def context_key(seed_url: str) -> str:
    """Readable, stable, filesystem-safe id for one seed URL."""
    parts = urlparse(seed_url)
    stem = _SLUG_RE.sub("-", (parts.path or "/").lower()).strip("-")
    if parts.query:
        stem = f"{stem}-q" if stem else "q"
    stem = stem[:_MAX_STEM].strip("-") or "root"
    digest = hashlib.sha256(seed_url.encode("utf-8")).hexdigest()[:8]
    return f"{stem}-{digest}"


class ContextStore:
    """Manifest storage for one seed URL's context dataset."""

    def __init__(self, seed_url: str, root: Optional[Path] = None):
        self.seed_url = seed_url
        self.site_slug = site_slug(seed_url)
        self.key = context_key(seed_url)
        self.cache = SnapshotCache(self.site_slug, root=root)
        self.dir = self.cache.dir / "context"
        self.dir.mkdir(parents=True, exist_ok=True)

    def manifest_path(self) -> Path:
        return self.dir / f"{self.key}.json"

    def save_manifest(self, manifest: Dict[str, Any]) -> Path:
        path = self.manifest_path()
        path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        return path

    def load_manifest(self) -> Optional[Dict[str, Any]]:
        return _read_json(self.manifest_path())

    def purge(self) -> None:
        """Drop this site's cached bodies (shared with the snapshot cache)."""
        self.cache.purge()
        self.dir.mkdir(parents=True, exist_ok=True)


def load_context_manifest(
    site_slug_value: str, key: str, root: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Load a stored manifest by (site_slug, context_key), or None.

    Both components are validated first: they arrive from callers (REST/MCP) and
    are joined into a filesystem path.
    """
    try:
        validate_slug(site_slug_value)
        validate_context_key(key)
    except (InvalidSlugError, InvalidContextKeyError):
        return None
    base = _contexts_root(root) / site_slug_value / "context" / f"{key}.json"
    return _read_json(base)


def list_contexts(root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Every stored context manifest, newest first, as light summary dicts."""
    base = _contexts_root(root)
    if not base.exists():
        return []
    out: List[Dict[str, Any]] = []
    for site_dir in sorted(base.iterdir()):
        ctx_dir = site_dir / "context"
        if not ctx_dir.is_dir():
            continue
        for path in sorted(ctx_dir.glob("*.json")):
            manifest = _read_json(path)
            if not manifest:
                continue
            out.append(
                {
                    "site_slug": site_dir.name,
                    "context_key": path.stem,
                    "seed_url": manifest.get("seed_url"),
                    "completed_at": manifest.get("completed_at"),
                    "pages": (manifest.get("stats") or {}).get("nodes_total", 0),
                    "depth": (manifest.get("config") or {}).get("depth"),
                    "analysis_method": manifest.get("analysis_method"),
                }
            )
    out.sort(key=lambda row: row.get("completed_at") or "", reverse=True)
    return out


def _contexts_root(root: Optional[Path]) -> Path:
    if root is None:
        try:
            from ...core.config import workspace_root

            root = workspace_root()
        except Exception:  # pragma: no cover - defensive
            root = Path(".aieo-workspace").resolve()
    return Path(root) / ".cache" / "snapshots"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
