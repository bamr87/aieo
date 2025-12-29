"""Audit API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import verify_api_key_simple as verify_api_key
from ...services.audit_service import AuditService


router = APIRouter()
audit_service = AuditService()


class AuditRequest(BaseModel):
    """Audit request model."""

    url: Optional[str] = None
    content: Optional[str] = None
    format: str = "markdown"


@router.post("/aieo/audit")
async def audit_content(
    request: AuditRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Audit content for AIEO score.

    Either url or content must be provided.
    """
    if not request.url and not request.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either url or content must be provided",
        )

    try:
        result = await audit_service.audit(
            url=request.url,
            content=request.content,
            format=request.format,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}",
        )
