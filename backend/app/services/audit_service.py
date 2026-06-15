"""Audit service for content analysis."""

import httpx
from typing import Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import redis
import json

from ..core.config import settings
from ..core.validation import validate_content_size, validate_url, sanitize_content
from ..core.errors import ContentTooLargeError, FetchFailedError
from ..core.monitoring import track_performance
from ..models.audit import Audit as AuditModel
from .scoring_engine import ScoringEngine
from .benchmark_service import BenchmarkService


class AuditService:
    """Service for auditing content."""

    def __init__(self):
        self.scoring_engine = ScoringEngine()
        self.benchmark_service = BenchmarkService()
        self._engines: Dict[tuple, ScoringEngine] = {}
        self.redis_client = (
            redis.Redis.from_url(settings.REDIS_URL) if settings.REDIS_URL else None
        )

    def _engine_for(
        self, provider: Optional[str], model: Optional[str]
    ) -> ScoringEngine:
        """Return a scoring engine for the requested provider/model.

        Falls back to the shared default engine when no override is given;
        otherwise builds and caches one per (provider, model) pair.
        """
        if not provider and not model:
            return self.scoring_engine
        key = (provider or "", model or "")
        engine = self._engines.get(key)
        if engine is None:
            engine = ScoringEngine(provider=provider, model=model)
            self._engines[key] = engine
        return engine

    @track_performance
    async def audit(
        self,
        url: Optional[str] = None,
        content: Optional[str] = None,
        format: str = "markdown",
        user_id: Optional[str] = None,
        db: Session = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict:
        """
        Audit content and return score with gaps.

        Args:
            url: URL to fetch content from
            content: Raw content string
            format: Content format ('markdown' or 'html')
            user_id: Optional user ID
            db: Database session
            provider: Optional scoring provider override (openai / anthropic /
                claude-cli / heuristic). When omitted, the server default is used.
            model: Optional model override for the chosen provider.

        Returns:
            Audit result dictionary
        """
        # Validate inputs
        if url:
            validate_url(url)
            content = await self._fetch_url(url)
            format = "html"
        elif content:
            content = sanitize_content(content)
            validate_content_size(content)
        else:
            raise ValueError("Either url or content must be provided")

        # Pick the scoring engine — a per-request one when a provider/model
        # override is supplied, else the shared default.
        engine = self._engine_for(provider, model)

        # Check cache (keyed by content + provider/model so overrides don't collide)
        cache_key = self._get_cache_key(content, provider, model, format)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        # Score content
        score_result = engine.score(content, format)

        # Generate benchmark
        benchmark = await self.benchmark_service.calculate_benchmark(
            content=content,
            score=score_result["score"],
        )

        # Build result — pass through the full scoring output (dimensions,
        # pattern_scores, scoring_method, provider, assessment, …) and layer
        # the benchmark on top.
        result = dict(score_result)
        result["fixes"] = []  # Will be populated by optimization service
        result["benchmark"] = benchmark

        # Cache result
        self._save_to_cache(cache_key, result)

        # Save to database if user_id provided
        if db and user_id:
            self._save_audit(db, user_id, content, url, result)

        return result

    async def _fetch_url(self, url: str) -> str:
        """Fetch content from URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "AIEO-Bot/1.0 (Content Analysis Tool)",
                    },
                )
                response.raise_for_status()

                # Check content size
                content = response.text
                if len(content) > settings.MAX_CONTENT_SIZE_BYTES:
                    raise ContentTooLargeError(
                        f"Fetched content exceeds maximum size limit ({settings.MAX_CONTENT_SIZE_BYTES} bytes)"
                    )

                return content
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise FetchFailedError(f"URL not found: {url}")
            elif e.response.status_code == 403:
                raise FetchFailedError(
                    f"Access forbidden: {url} (may require authentication)"
                )
            raise FetchFailedError(
                f"Failed to fetch URL: HTTP {e.response.status_code}"
            )
        except httpx.TimeoutException:
            raise FetchFailedError(f"Request timeout: {url}")
        except Exception as e:
            raise FetchFailedError(f"Error fetching URL: {str(e)}")

    def _get_cache_key(
        self,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        format: str = "markdown",
    ) -> str:
        """Generate cache key from content hash + provider/model/format."""
        from .content_parser import ContentParser

        parser = ContentParser()
        suffix = f"{provider or 'default'}:{model or 'default'}:{format}"
        return f"audit:{parser._hash_content(content)}:{suffix}"

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get cached audit result."""
        if not self.redis_client:
            return None

        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        return None

    def _save_to_cache(self, cache_key: str, result: Dict):
        """Save audit result to cache."""
        if not self.redis_client:
            return

        try:
            ttl = settings.REDIS_CACHE_TTL
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result),
            )
        except Exception:
            pass

    def _save_audit(
        self,
        db: Session,
        user_id: str,
        content: str,
        url: Optional[str],
        result: Dict,
    ):
        """Save audit result to database."""
        from .content_parser import ContentParser

        parser = ContentParser()
        content_hash = parser._hash_content(content)

        audit = AuditModel(
            user_id=user_id,
            content_hash=content_hash,
            url=url,
            score=result["score"],
            grade=result["grade"],
            gaps=result["gaps"],
            fixes=result.get("fixes", []),
            benchmark=result["benchmark"],
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )

        db.add(audit)
        db.commit()
