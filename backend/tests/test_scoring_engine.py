"""Tests for scoring engine."""
import pytest
from app.services.scoring_engine import ScoringEngine


def test_score_basic_content():
    """Test scoring basic content."""
    engine = ScoringEngine()
    content = "# Test Article\n\nThis is a test article."
    
    result = engine.score(content)
    
    assert "score" in result
    assert "grade" in result
    assert "gaps" in result
    assert 0 <= result["score"] <= 100
    assert result["grade"] in ["A+", "A", "B", "C", "D", "F"]


def test_score_with_tables():
    """Test scoring content with tables."""
    engine = ScoringEngine()
    content = """# Test Article

| Feature | Value |
|---------|-------|
| Test    | 123   |
"""
    
    result = engine.score(content)
    
    # Should score higher due to structured data
    assert result["score"] > 0


def test_score_with_entities():
    """Test scoring content with entities."""
    engine = ScoringEngine()
    content = """# Test Article

OpenAI released GPT-4 in March 2023. Anthropic's Claude was released in 2024.
"""
    
    result = engine.score(content)
    
    # Should detect entities
    assert result["score"] > 0


def test_gap_generation():
    """Test gap generation."""
    engine = ScoringEngine()
    content = "# Test\n\nSimple content without patterns."
    
    result = engine.score(content)
    
    # Should have gaps
    assert len(result["gaps"]) > 0
    assert all("category" in gap for gap in result["gaps"])


