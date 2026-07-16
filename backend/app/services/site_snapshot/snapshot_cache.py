"""Per-site incremental HTTP cache for the crawler.

Modeled on ``integrations/cache.py`` (JSON under ``workspace_root()/.cache``)
but byte-aware: a small greppable JSON sidecar per URL plus the raw response
body gzipped alongside it. Enables conditional GET (ETag / Last-Modified) so
re-runs only re-download changed pages, and serves as the offline backup
substrate so any export can be regenerated with no network.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

try:
    from ...core.config import workspace_root
except Exception:  # pragma: no cover

    def workspace_root() -> Path:
        return Path(".aieo-workspace").resolve()


CACHE_VERSION = "4"

# A site slug is only ever a host (dots->'_', optional '_port'); it must never
# contain path separators or '..'. Surfaces accept caller-supplied slugs, so
# this is enforced before it is joined into a filesystem path.
_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")


class InvalidSlugError(ValueError):
    """Raised when a site_slug would escape the cache root."""


def validate_slug(slug: str) -> str:
    if not slug or not _SLUG_RE.fullmatch(slug):
        raise InvalidSlugError(f"Invalid site slug: {slug!r}")
    return slug


def site_slug(base_url: str) -> str:
    """Stable directory name for a site: host without 'www.', dots -> '_'."""
    netloc = (urlparse(base_url).netloc or base_url).lower()
    if "@" in netloc:
        netloc = netloc.split("@", 1)[1]
    host, _, port = netloc.partition(":")
    if host.startswith("www."):
        host = host[4:]
    slug = host.replace(".", "_") or "site"
    if port and port not in ("80", "443"):
        slug = f"{slug}_{port}"
    return slug


class SnapshotCache:
    """Filesystem cache for one site's crawl, rooted under the workspace."""

    def __init__(self, slug: str, root: Optional[Path] = None):
        validate_slug(slug)
        base = root or workspace_root()
        snapshots_root = (Path(base) / ".cache" / "snapshots").resolve()
        self.dir = (snapshots_root / slug).resolve()
        # Defense in depth: never let a slug escape the snapshots root.
        if self.dir != snapshots_root and not self.dir.is_relative_to(snapshots_root):
            raise InvalidSlugError(f"Slug escapes cache root: {slug!r}")
        self.pages_dir = self.dir / "pages"
        self.raw_dir = self.dir / "raw"
        self.records_dir = self.dir / "records"
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.records_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def url_key(normalized_url: str) -> str:
        return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:24]

    def _sidecar_path(self, key: str) -> Path:
        return self.pages_dir / f"{key}.json"

    def _body_path(self, key: str) -> Path:
        return self.raw_dir / f"{key}.body.gz"

    def load(self, normalized_url: str) -> Optional[Dict[str, Any]]:
        """Return the cached sidecar for a URL, or None on miss/collision/version skew."""
        key = self.url_key(normalized_url)
        path = self._sidecar_path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
        # Detect a (vanishingly rare) truncated-key collision and version skew.
        if entry.get("url") != normalized_url:
            return None
        if entry.get("cache_version") != CACHE_VERSION:
            return None
        return entry

    def read_body(self, normalized_url: str) -> Optional[str]:
        key = self.url_key(normalized_url)
        path = self._body_path(key)
        if not path.exists():
            return None
        try:
            return gzip.decompress(path.read_bytes()).decode("utf-8", errors="replace")
        except (OSError, ValueError):
            return None

    def _record_path(self, key: str) -> Path:
        return self.records_dir / f"{key}.json"

    def save(
        self,
        normalized_url: str,
        *,
        status: int,
        content_type: Optional[str],
        text: str,
        content_hash: str,
        fetched_at: str,
        etag: Optional[str],
        last_modified: Optional[str],
        truncated: bool = False,
    ) -> Dict[str, Any]:
        key = self.url_key(normalized_url)
        self._body_path(key).write_bytes(gzip.compress(text.encode("utf-8")))
        entry = {
            "cache_version": CACHE_VERSION,
            "url": normalized_url,
            "url_key": key,
            "status": status,
            "content_type": content_type,
            "content_hash": content_hash,
            "etag": etag,
            "last_modified": last_modified,
            "fetched_at": fetched_at,
            "truncated": truncated,
        }
        self._sidecar_path(key).write_text(
            json.dumps(entry, indent=2), encoding="utf-8"
        )
        return entry

    def update_fetched_at(self, normalized_url: str, fetched_at: str) -> None:
        """Rewrite only the sidecar's fetched_at (used after a 304 revalidation)."""
        key = self.url_key(normalized_url)
        path = self._sidecar_path(key)
        if not path.exists():
            return
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return
        entry["fetched_at"] = fetched_at
        path.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    def save_record(self, normalized_url: str, record: Dict[str, Any]) -> None:
        """Persist the extracted PageRecord so unchanged re-runs skip re-parsing."""
        key = self.url_key(normalized_url)
        self._record_path(key).write_text(
            json.dumps(record, default=str), encoding="utf-8"
        )

    def load_record(self, normalized_url: str) -> Optional[Dict[str, Any]]:
        key = self.url_key(normalized_url)
        path = self._record_path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    @staticmethod
    def conditional_headers(entry: Dict[str, Any]) -> Dict[str, str]:
        """If-None-Match / If-Modified-Since, with validators sent verbatim."""
        headers: Dict[str, str] = {}
        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
        if entry.get("last_modified"):
            headers["If-Modified-Since"] = entry["last_modified"]
        return headers

    @staticmethod
    def is_fresh(entry: Dict[str, Any], ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            return False
        from datetime import datetime, timezone

        try:
            fetched = datetime.fromisoformat(entry["fetched_at"])
        except (KeyError, ValueError):
            return False
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - fetched).total_seconds()
        return age < ttl_seconds

    def manifest_path(self) -> Path:
        return self.dir / "_manifest.json"

    def save_manifest(self, manifest: Dict[str, Any]) -> Path:
        path = self.manifest_path()
        path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        return path

    def load_manifest(self) -> Optional[Dict[str, Any]]:
        path = self.manifest_path()
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    def purge(self) -> int:
        """Delete this site's cache dir entirely; returns files removed."""
        count = sum(1 for _ in self.dir.rglob("*") if _.is_file())
        shutil.rmtree(self.dir, ignore_errors=True)
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        return count
