"""Citations API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from ...core.database import get_db
from ...core.security import verify_api_key
from ...services.citation_tracker import CitationTracker


router = APIRouter()
citation_tracker = CitationTracker()


@router.get("/aieo/citations")
async def get_citations(
    url: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    engine: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    List citations for URL/domain.
    """
    citations = citation_tracker.get_citations(
        db=db,
        url=url,
        domain=domain,
        engine=engine,
        days=30,
    )

    # Apply limit
    citations = citations[:limit]

    # Convert to dict format
    data = [
        {
            "id": str(c.id),
            "url": c.url,
            "domain": c.domain,
            "engine": c.engine,
            "prompt": c.prompt,
            "citation_text": c.citation_text,
            "position": c.position,
            "confidence": c.confidence,
            "detected_at": c.detected_at.isoformat(),
        }
        for c in citations
    ]

    return {
        "data": data,
        "pagination": {
            "next_cursor": None,  # Cursor pagination - to be implemented in v1.1
            "has_more": len(citations) >= limit,
            "total_count": len(citations),
        },
    }


@router.get("/aieo/dashboard")
async def get_dashboard(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Get share-of-voice metrics.
    """
    return citation_tracker.get_dashboard_data(db=db)
