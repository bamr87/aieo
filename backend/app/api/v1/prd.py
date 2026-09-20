"""PRD lineage API endpoints."""

from typing import List, Optional

import anyio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import verify_api_key_simple as verify_api_key
from ...services.prd_lineage import PrdConfig, PrdInventory, PrdLineageService
from ...services.prd_lineage import exporters

router = APIRouter()
prd_service = PrdLineageService()

_MEDIA = {
    "json": "application/json",
    "markdown": "text/markdown; charset=utf-8",
    "mermaid": "text/plain; charset=utf-8",
}


class PrdRequest(BaseModel):
    repo_root: str
    formats: Optional[List[str]] = None
    map_only: bool = False
    max_files: int = 400
    agent_enabled: bool = True
    agent_model: Optional[str] = None
    agent_max_sources: int = 12
    agent_synthesis: bool = True


@router.post("/aieo/prd")
async def create_prd_inventory(
    request: PrdRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    try:
        cfg = PrdConfig.from_dict(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        return await anyio.to_thread.run_sync(
            lambda: prd_service.run(
                request.repo_root,
                formats=request.formats,
                cfg=cfg,
                map_only=request.map_only,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aieo/prd")
async def list_prd_inventories(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return {"inventories": prd_service.list_inventories()}


@router.get("/aieo/prd/{repo_slug}")
async def get_prd_inventory(
    repo_slug: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    manifest = prd_service.load_manifest(repo_slug)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"No PRD inventory for {repo_slug}")
    return manifest


@router.get("/aieo/prd/{repo_slug}/export/{fmt}")
async def export_prd_inventory(
    repo_slug: str,
    fmt: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    if fmt not in exporters.FORMATS:
        raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")
    manifest = prd_service.load_manifest(repo_slug)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"No PRD inventory for {repo_slug}")
    inv = PrdInventory.from_dict(manifest)
    text = await anyio.to_thread.run_sync(lambda: exporters.render(inv, fmt))
    media = _MEDIA.get(fmt, "text/plain; charset=utf-8")
    if fmt in ("markdown", "mermaid"):
        return PlainTextResponse(text, media_type=media)
    return Response(content=text, media_type=media)
