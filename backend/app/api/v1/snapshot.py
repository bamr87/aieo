"""Site snapshot API endpoints.

Thin wrapper over :class:`SiteSnapshotService` mirroring the content router's
conventions (module-level service singleton; api-key + db deps immediately
discarded). Crawls are synchronous, blocking I/O so they run off the event loop.
"""

from typing import List, Optional

import anyio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import verify_api_key_simple as verify_api_key
from ...services.site_snapshot import CrawlConfig, SiteSnapshot, SiteSnapshotService
from ...services.site_snapshot import exporters

router = APIRouter()
snapshot_service = SiteSnapshotService()

_MEDIA = {
    "text": "text/plain; charset=utf-8",
    "markdown": "text/markdown; charset=utf-8",
    "json": "application/json",
    "html": "text/html; charset=utf-8",
    "pdf": "application/pdf",
    "bundle": "application/zip",
}


class SnapshotRequest(BaseModel):
    base_url: str
    formats: Optional[List[str]] = None
    max_pages: int = 500
    max_depth: int = 6
    max_link_pages: int = 200
    delay_seconds: float = 0.25
    ttl_seconds: int = 0
    respect_robots: bool = True
    use_cache: bool = True
    include_external: bool = False
    include_assets: bool = False
    strip_boilerplate: bool = True
    refresh: bool = False


@router.post("/aieo/snapshot")
async def create_snapshot(
    request: SnapshotRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Crawl a site and write offline snapshot files; returns a summary + stats."""
    del api_key, db
    cfg = CrawlConfig.from_dict(request.model_dump())
    try:
        return await anyio.to_thread.run_sync(
            lambda: snapshot_service.snapshot(
                request.base_url, formats=request.formats, cfg=cfg
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/aieo/snapshot")
async def list_snapshots(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return {"snapshots": snapshot_service.list_snapshots()}


@router.get("/aieo/snapshot/{site_slug}/manifest")
async def get_manifest(
    site_slug: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    manifest = snapshot_service.load_manifest(site_slug)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"No snapshot for {site_slug}")
    return manifest


@router.get("/aieo/snapshot/{site_slug}/export/{fmt}")
async def export_snapshot(
    site_slug: str,
    fmt: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Re-render a stored snapshot in any format offline (from the cached manifest)."""
    del api_key, db
    if fmt not in exporters.FORMATS:
        raise HTTPException(status_code=422, detail=f"Unknown format {fmt!r}")
    manifest = snapshot_service.load_manifest(site_slug)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"No snapshot for {site_slug}")
    site = SiteSnapshot.from_dict(manifest)
    # Rendering (markdown->HTML per page, zip, PDF) is heavy and synchronous —
    # run it off the event loop, like the POST and MCP paths.
    data, _engine, _is_text = await anyio.to_thread.run_sync(
        lambda: exporters.render(site, fmt)
    )
    media = _MEDIA.get(fmt, "application/octet-stream")
    if fmt in ("text", "markdown"):
        return PlainTextResponse(content=data.decode("utf-8"), media_type=media)
    return Response(content=data, media_type=media)
