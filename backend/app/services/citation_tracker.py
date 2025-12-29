"""Citation tracking service."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import openai

from ..core.config import settings
from ..models.citation import Citation


class CitationTracker:
    """Service for tracking citations across AI engines."""

    def __init__(self):
        self.qdrant_client = (
            QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
            if settings.QDRANT_URL
            else None
        )

    async def probe_engines(
        self,
        url: str,
        prompts: List[str],
        engines: List[str] = None,
    ) -> List[Dict]:
        """
        Probe AI engines with prompts and detect citations.

        Args:
            url: URL to check citations for
            prompts: List of prompts to test
            engines: List of engines to probe (default: from config)

        Returns:
            List of detected citations
        """
        if not engines:
            engines = settings.CITATION_DETECTION_ENGINES

        citations = []

        for engine in engines:
            for prompt in prompts:
                try:
                    citation = await self._probe_engine(engine, prompt, url)
                    if citation:
                        citations.append(citation)
                except Exception as e:
                    # Log error but continue
                    print(f"Error probing {engine}: {e}")

        return citations

    async def _probe_engine(self, engine: str, prompt: str, url: str) -> Optional[Dict]:
        """
        Probe a single engine with a prompt.

        Note: Actual implementation requires:
        1. API access to each engine (or web scraping with ToS compliance)
        2. Response parsing to detect citations
        3. URL matching logic

        For MVP, this is a placeholder that would be implemented based on:
        - Engine API availability
        - Legal/ToS compliance
        - Partnership agreements
        """
        # Placeholder implementation
        # In production, this would:
        # 1. Send prompt to engine API (if available)
        # 2. Parse response for citations
        # 3. Check if URL is cited
        # 4. Extract citation text and position

        # Example structure for when implemented:
        # try:
        #     response = await engine_client.query(prompt)
        #     citations = parse_citations(response, url)
        #     return citations[0] if citations else None
        # except Exception as e:
        #     logger.error(f"Error probing {engine}: {e}")
        #     return None

        return None

    def store_citations(self, db: Session, citations: List[Dict]):
        """Store citations in database."""
        for citation_data in citations:
            citation = Citation(
                url=citation_data["url"],
                domain=self._extract_domain(citation_data["url"]),
                engine=citation_data["engine"],
                prompt=citation_data["prompt"],
                prompt_category=citation_data.get("prompt_category"),
                citation_text=citation_data["citation_text"],
                position=citation_data.get("position"),
                confidence=citation_data.get("confidence", 1.0),
                detected_at=datetime.utcnow(),
                verified=False,
            )
            db.add(citation)

        db.commit()

    def get_citations(
        self,
        db: Session,
        url: Optional[str] = None,
        domain: Optional[str] = None,
        engine: Optional[str] = None,
        days: int = 30,
    ) -> List[Citation]:
        """Get citations from database."""
        query = db.query(Citation)

        if url:
            query = query.filter(Citation.url == url)
        if domain:
            query = query.filter(Citation.domain == domain)
        if engine:
            query = query.filter(Citation.engine == engine)

        # Filter by date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Citation.detected_at >= cutoff_date)

        return query.order_by(Citation.detected_at.desc()).all()

    def get_dashboard_data(self, db: Session, user_id: Optional[str] = None) -> Dict:
        """Get dashboard aggregation data."""
        # Get citations from last 30 days
        citations = self.get_citations(db, days=30)

        # Aggregate by engine
        by_engine = {}
        for citation in citations:
            engine = citation.engine
            by_engine[engine] = by_engine.get(engine, 0) + 1

        # Top cited pages
        url_counts = {}
        for citation in citations:
            url = citation.url
            url_counts[url] = url_counts.get(url, 0) + 1

        top_cited = [
            {"url": url, "count": count}
            for url, count in sorted(
                url_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        return {
            "citation_rate": [],  # Placeholder for time series
            "by_engine": by_engine,
            "top_cited_pages": top_cited,
        }

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc or url
