"""Tests for scoring engine.

Tests run in heuristic mode (no API key) to ensure the engine
works without external dependencies. AI-driven scoring is tested
separately with integration tests.
"""

from app.services.scoring_engine import ScoringEngine, _heuristic_anti_patterns
from app.services.prompt_loader import PromptLoader


def _make_engine():
    """Create engine with no API key (heuristic mode)."""
    return ScoringEngine(api_key=None)


def test_score_basic_content():
    """Test scoring basic content in heuristic mode."""
    engine = _make_engine()
    content = "# Test Article\n\nThis is a test article."

    result = engine.score(content)

    assert "score" in result
    assert "grade" in result
    assert "gaps" in result
    assert "pattern_scores" in result
    assert "word_count" in result
    assert "scoring_method" in result
    assert 0 <= result["score"] <= 100
    assert result["grade"] in ["A+", "A", "B", "C", "D", "F"]
    assert result["scoring_method"] == "heuristic"


def test_score_with_tables():
    """Test scoring content with tables."""
    engine = _make_engine()
    content = """# Test Article

| Feature | Value |
|---------|-------|
| Test    | 123   |
"""

    result = engine.score(content)

    assert result["score"] >= 0
    # Structured data pattern should detect the table
    sd = result["pattern_scores"].get("structured_data", {})
    assert sd.get("score", 0) > 0


def test_score_with_entities():
    """Test scoring content with entities."""
    engine = _make_engine()
    content = """# Test Article

OpenAI released GPT-4 in March 2023. Anthropic's Claude was released in 2024.
"""

    result = engine.score(content)

    assert result["score"] >= 0
    ed = result["pattern_scores"].get("entity_density", {})
    assert ed.get("detected", False)


def test_gap_generation():
    """Test gap generation."""
    engine = _make_engine()
    content = "# Test\n\nSimple content without patterns."

    result = engine.score(content)

    assert len(result["gaps"]) > 0
    assert all("category" in gap for gap in result["gaps"])
    assert all("severity" in gap for gap in result["gaps"])
    assert all("description" in gap for gap in result["gaps"])


def test_prompt_loader_loads_patterns():
    """Verify prompt files load correctly."""
    loader = PromptLoader()
    patterns = loader.load_patterns()

    assert len(patterns) == 10
    for p in patterns:
        assert "name" in p
        assert "weight" in p
        assert "max_score" in p
        assert "body" in p
        assert p["weight"] > 0
        assert p["max_score"] > 0


def test_prompt_loader_system_and_rubric():
    """Verify system prompt and rubric load."""
    loader = PromptLoader()
    system = loader.load_system_prompt()
    rubric = loader.load_rubric()

    assert "AIEO" in system
    assert "JSON" in rubric


def test_total_weights_sum_to_expected():
    """Pattern weights should sum to a known total."""
    loader = PromptLoader()
    patterns = loader.load_patterns()
    total = sum(p["weight"] for p in patterns)
    # Current weights: 20+15+10+15+10+15+10+5+15+10 = 125
    assert total == 125


def test_result_has_new_fields():
    """New engine returns enriched result format."""
    engine = _make_engine()
    content = "# Test\n\nBasic content for testing."

    result = engine.score(content)

    # New fields from the AI-driven architecture
    assert "scoring_method" in result
    assert "content_type" in result
    assert "overall_assessment" in result
    assert "anti_pattern_details" in result
    # Pattern scores have evidence and recommendation fields
    for name, data in result["pattern_scores"].items():
        assert "evidence" in data
        assert "recommendation" in data


def test_density_anti_pattern_spares_rich_content():
    """The structural-density anti-pattern should penalize a thin skeleton
    (lots of structure, little prose), not legitimately rich content."""
    rich = {
        "text": " ".join(f"word{i % 50}" for i in range(400)),
        "word_count": 400,
        "tables": [{}],
        "lists": [{}, {}],
        "headers": [{}, {}, {}],  # 6 elements / 400 words = ~67 words/element
    }
    skeleton = {
        "text": "a b c d e f g h i j",
        "word_count": 10,
        "tables": [],
        "lists": [{}, {}, {}],
        "headers": [{}, {}, {}],  # 6 elements / 10 words = ~1.7 words/element
    }
    assert _heuristic_anti_patterns(rich) == 0
    assert _heuristic_anti_patterns(skeleton) >= 20
