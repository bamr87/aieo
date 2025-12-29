"""Patterns API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import verify_api_key_simple as verify_api_key

router = APIRouter()


# Pattern library data (in production, this would be in a database)
PATTERNS = [
    {
        "id": "structured_data",
        "name": "Structured Data",
        "category": "structure",
        "description": "Convert prose into tables, lists, structured formats",
        "citation_boost": {"min": 15, "max": 25},
    },
    {
        "id": "entity_density",
        "name": "Entity Density",
        "category": "content",
        "description": "Increase named entities (people, places, products, dates) per paragraph",
        "citation_boost": {"min": 10, "max": 20},
    },
    {
        "id": "citation_hooks",
        "name": "Citation Hooks",
        "category": "metadata",
        "description": "Explicit source attribution: 'According to [source]', '[Study] found...'",
        "citation_boost": {"min": 5, "max": 15},
    },
    {
        "id": "recursive_depth",
        "name": "Recursive Depth",
        "category": "content",
        "description": "Answer questions within questions (nested Q&A format)",
        "citation_boost": {"min": 20, "max": 30},
    },
    {
        "id": "temporal_anchoring",
        "name": "Temporal Anchoring",
        "category": "metadata",
        "description": "Explicit dates, version numbers, 'as of [date]' statements",
        "citation_boost": {"min": 10, "max": 15},
    },
    {
        "id": "comparison_tables",
        "name": "Comparison Tables",
        "category": "format",
        "description": "Side-by-side comparisons in tabular format",
        "citation_boost": {"min": 25, "max": 40},
    },
    {
        "id": "definitional_precision",
        "name": "Definitional Precision",
        "category": "content",
        "description": "Explicit definitions: 'X is defined as...', 'X means...'",
        "citation_boost": {"min": 8, "max": 12},
    },
    {
        "id": "step_by_step",
        "name": "Step-by-Step Procedures",
        "category": "format",
        "description": "Numbered steps: 'Step 1: ... Step 2: ...'",
        "citation_boost": {"min": 12, "max": 18},
    },
    {
        "id": "faq_injection",
        "name": "FAQ Injection",
        "category": "content",
        "description": "Anticipate and answer common questions inline",
        "citation_boost": {"min": 15, "max": 25},
    },
    {
        "id": "meta_context",
        "name": "Meta-Context",
        "category": "content",
        "description": "Explain why information matters: 'This is important because...'",
        "citation_boost": {"min": 5, "max": 10},
    },
]


@router.get("/aieo/patterns")
async def list_patterns(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Browse pattern library.
    """
    return {"patterns": PATTERNS}


class ApplyPatternRequest(BaseModel):
    """Apply pattern request model."""

    content: str


@router.post("/aieo/patterns/{pattern_id}/apply")
async def apply_pattern(
    pattern_id: str,
    request: ApplyPatternRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Apply pattern to content.
    """
    # Find pattern
    pattern = next((p for p in PATTERNS if p["id"] == pattern_id), None)
    if not pattern:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern {pattern_id} not found",
        )

    # For MVP, return content as-is
    # In production, this would apply the specific pattern
    return {
        "optimized_content": request.content,
        "pattern_id": pattern_id,
        "pattern_name": pattern["name"],
    }
