"""Optimize API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import logging

from ...core.database import get_db
from ...core.security import verify_api_key_simple as verify_api_key
from ...services.optimize_service import OptimizeService


router = APIRouter()
optimize_service = OptimizeService()


class OptimizeRequest(BaseModel):
    """Optimize request model."""

    content: str
    target_engines: Optional[list[str]] = None
    style: str = "preserve"


@router.post("/aieo/optimize")
async def optimize_content(
    request: OptimizeRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Optimize content with AIEO patterns.
    """
    if not request.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content is required",
        )

    try:
        result = await optimize_service.optimize(
            content=request.content,
            target_engines=request.target_engines,
            style=request.style,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": str(e),
                }
            },
        )
    except Exception as e:
        logger = logging.getLogger("aieo")
        logger.error(f"Optimization error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal error occurred during optimization",
                }
            },
        )
