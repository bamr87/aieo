"""Site context API endpoints.

Thin wrapper over :class:`SiteContextService`, mirroring the snapshot router's
conventions (module-level service singleton; api-key + db deps immediately
discarded). Builds are synchronous, blocking I/O — and the agent pass shells out
to the Claude Code CLI — so they run off the event loop via a worker thread.
"""

from typing import List, Optional

import anyio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import verify_api_key_simple as verify_api_key
from ...services.site_context import ContextConfig, SiteContext, SiteContextService
from ...services.site_context import exporters

router = APIRouter()
context_service = SiteContextService()

_MEDIA = {
    "json": "application/json",
    "markdown": "text/markdown; charset=utf-8",
    "html": "text/html; charset=utf-8",
    "mermaid": "text/plain; charset=utf-8",
}


class ContextRequest(BaseModel):
    """Every knob is optional; only ``seed_url`` is required."""

    seed_url: str
    formats: Optional[List[str]] = None
    map_only: bool = False
    # phase 1
    depth: int = 2
    scope: str = "host"
    max_pages: int = 150
    max_pages_per_level: int = 80
    follow_sitemap: bool = False
    include_external: bool = False
    delay_seconds: float = 0.25
    ttl_seconds: int = 0
    respect_robots: bool = True
    use_cache: bool = True
    refresh: bool = False
    # phase 2
    strip_boilerplate: bool = True
    keep_interactive: bool = True
    capture_presentation: bool = True
    fetch_stylesheets: bool = True
    fetch_scripts: bool = True
    extractor: str = "auto"
    use_optional_libraries: bool = True
    render: bool = False
    render_wait_ms: int = 600
    # phase 3 (Claude Code CLI over OAuth)
    agent_enabled: bool = True
    agent_model: Optional[str] = None
    agent_max_pages: int = 25
    agent_concurrency: int = 3
    agent_synthesis: bool = True


@router.post("/aieo/context")
async def create_context(
    request: ContextRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Crawl a URL N levels down and build the contextual dataset."""
    del api_key, db
    try:
        cfg = ContextConfig.from_dict(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        return await anyio.to_thread.run_sync(
            lambda: context_service.run(
                request.seed_url,
                formats=request.formats,
                cfg=cfg,
                map_only=request.map_only,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aieo/context")
async def list_contexts(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Every stored context dataset, newest first."""
    del api_key, db
    return {"contexts": context_service.list_contexts()}


@router.get("/aieo/context/{site_slug}/{context_key}")
async def get_context(
    site_slug: str,
    context_key: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Return a stored dataset without re-crawling."""
    del api_key, db
    manifest = context_service.load_manifest(site_slug, context_key)
    if not manifest:
        raise HTTPException(
            status_code=404, detail=f"No context for {site_slug}/{context_key}"
        )
    return manifest


@router.get("/aieo/context/{site_slug}/{context_key}/export/{fmt}")
async def export_context(
    site_slug: str,
    context_key: str,
    fmt: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Re-render a stored dataset in any format offline (from the manifest)."""
    del api_key, db
    if fmt not in exporters.FORMATS:
        raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")
    manifest = context_service.load_manifest(site_slug, context_key)
    if not manifest:
        raise HTTPException(
            status_code=404, detail=f"No context for {site_slug}/{context_key}"
        )
    ctx = SiteContext.from_dict(manifest)
    text = await anyio.to_thread.run_sync(lambda: exporters.render(ctx, fmt))
    media = _MEDIA.get(fmt, "text/plain; charset=utf-8")
    if fmt in ("markdown", "mermaid"):
        return PlainTextResponse(text, media_type=media)
    return Response(content=text, media_type=media)
