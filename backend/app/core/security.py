"""Security utilities for authentication and authorization."""

from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from .database import get_db
from ..models.api_key import APIKey


async def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> str:
    """
    Verify API key from request header.

    Checks against database, validates expiration, and tracks usage.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Hash the provided key
    key_hash = APIKey.hash_key(x_api_key)

    # Look up in database
    api_key = (
        db.query(APIKey)
        .filter(APIKey.key_hash == key_hash, APIKey.is_active == True)
        .first()
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # Update usage tracking
    api_key.last_used_at = datetime.utcnow()
    api_key.usage_count += 1
    db.commit()

    return x_api_key


async def verify_api_key_simple(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Simple API key verification for MVP/testing.

    Accepts any key >10 characters. Use verify_api_key for production.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if len(x_api_key) < 10:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return x_api_key
