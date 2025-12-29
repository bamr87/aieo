"""Input validation utilities."""
import re
from typing import Optional
from ..core.config import settings


def validate_content_size(content: str) -> None:
    """Validate content size."""
    word_count = len(content.split())
    char_count = len(content)
    
    if word_count > settings.MAX_CONTENT_WORDS:
        raise ValueError(
            f"Content exceeds maximum word limit ({settings.MAX_CONTENT_WORDS} words). "
            f"Current: {word_count} words. Please split into smaller documents."
        )
    
    if char_count > settings.MAX_CONTENT_SIZE_BYTES:
        raise ValueError(
            f"Content exceeds maximum size limit ({settings.MAX_CONTENT_SIZE_BYTES} bytes). "
            f"Current: {char_count} bytes."
        )


def validate_url(url: str) -> None:
    """Validate URL format."""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        raise ValueError(f"Invalid URL format: {url}")


def sanitize_content(content: str) -> str:
    """Sanitize content to prevent injection attacks."""
    # Remove null bytes
    content = content.replace('\x00', '')
    
    # Limit content length
    if len(content) > settings.MAX_CONTENT_SIZE_BYTES:
        content = content[:settings.MAX_CONTENT_SIZE_BYTES]
    
    return content

