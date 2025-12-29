"""Rate limiting middleware."""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
from collections import defaultdict
from typing import Dict, Tuple

from .config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.requests: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Get API key from header
        api_key = request.headers.get("X-API-Key", "anonymous")
        
        # Check rate limit
        if not self._check_rate_limit(api_key):
            return Response(
                content='{"error": {"code": "RATE_LIMITED", "message": "Rate limit exceeded. Retry after 60 seconds.", "retry_after": 60}}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )
        
        response = await call_next(request)
        return response
    
    def _check_rate_limit(self, key: str) -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[key]) >= self.requests_per_minute:
            return False
        
        # Record request
        self.requests[key].append(now)
        return True

