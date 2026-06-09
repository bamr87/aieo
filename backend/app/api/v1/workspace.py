"""Workspace API endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.config import workspace_root
from ...core.database import get_db
from ...core.security import verify_api_key_simple as verify_api_key
from ...services.workspace_service import WorkspaceService


router = APIRouter()
workspace_service = WorkspaceService(root=workspace_root())


class WorkspaceReadRequest(BaseModel):
    path: str


class WorkspaceWriteRequest(BaseModel):
    path: str
    content: str


class WorkspaceMoveRequest(BaseModel):
    source_path: str
    destination_path: str


@router.post("/aieo/workspace/init")
async def initialize_workspace(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return workspace_service.initialize()


@router.get("/aieo/workspace/tree")
async def list_workspace(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return {"nodes": [node.__dict__ for node in workspace_service.list_tree()]}


@router.post("/aieo/workspace/read")
async def read_workspace_file(
    request: WorkspaceReadRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    try:
        return workspace_service.read_file(request.path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/aieo/workspace/write")
async def write_workspace_file(
    request: WorkspaceWriteRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    try:
        return workspace_service.write_file(request.path, request.content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/aieo/workspace/move")
async def move_workspace_file(
    request: WorkspaceMoveRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    try:
        return workspace_service.move_file(request.source_path, request.destination_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source file not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
