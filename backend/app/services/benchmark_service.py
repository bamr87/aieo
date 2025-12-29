"""Benchmark service for comparing content against top-cited content."""

from typing import Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)
import openai
from ..core.config import settings


class BenchmarkService:
    """Service for benchmarking content against top-cited content."""

    def __init__(self):
        self.qdrant_client = None
        if settings.QDRANT_URL:
            try:
                self.qdrant_client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                )
            except Exception:
                pass

    async def calculate_benchmark(
        self,
        content: str,
        score: float,
    ) -> Dict:
        """
        Calculate benchmark percentile and engine-specific scores.

        Args:
            content: Content to benchmark
            score: AIEO score of the content

        Returns:
            Benchmark dictionary with percentile and engine scores
        """
        # For MVP, return placeholder benchmark
        # In production, this would:
        # 1. Generate embedding for content
        # 2. Query Qdrant for similar high-scoring content
        # 3. Calculate percentile ranking
        # 4. Estimate engine-specific scores

        # Simple percentile calculation based on score
        # Assuming score distribution: most content scores 30-70
        if score >= 90:
            percentile = 95
        elif score >= 80:
            percentile = 85
        elif score >= 70:
            percentile = 70
        elif score >= 60:
            percentile = 50
        elif score >= 50:
            percentile = 30
        else:
            percentile = 15

        # Placeholder engine scores (would be calculated from historical data)
        engine_scores = {
            "grok": max(0, score - 5),
            "claude": max(0, score - 3),
            "gpt": max(0, score - 2),
        }

        return {
            "percentile": percentile,
            "engine_scores": engine_scores,
        }

    async def _generate_embedding(self, text: str) -> list:
        """Generate embedding for text using OpenAI."""
        if not settings.OPENAI_API_KEY:
            return None

        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=text[:8000],  # Limit input size
            )
            return response.data[0].embedding
        except Exception:
            return None
