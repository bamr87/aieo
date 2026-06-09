from app.analyzers import (
    ContentLengthComparator,
    ContentScorer,
    CROChecker,
    KeywordAnalyzer,
    LandingPageScorer,
    ReadabilityScorer,
    SearchIntentAnalyzer,
    SEOQualityRater,
)


def test_readability_and_seo():
    text = "# Title\n\n## Section\n\nThis is a short sentence. This is another one."
    readability = ReadabilityScorer().score(text)
    seo = SEOQualityRater().rate(text)
    assert 0 <= readability["score"] <= 100
    assert 0 <= seo["score"] <= 100


def test_keyword_intent_length_humanity():
    text = "Content marketing strategy guide for B2B SaaS teams."
    keyword = KeywordAnalyzer().analyze(text, primary_keyword="content")
    intent = SearchIntentAnalyzer().analyze(text)
    length = ContentLengthComparator().compare(text, [100, 200, 300])
    humanity = ContentScorer().score(text)
    assert "primary" in keyword
    assert intent["intent"] in {"informational", "navigational", "transactional", "commercial"}
    assert "optimal_target" in length
    assert "humanity" in humanity


def test_cro_analyzers():
    text = "# Landing\n\nTrusted by teams.\n\nStart trial today.\n"
    landing = LandingPageScorer().score(text)
    checks = CROChecker().check(text)
    assert 0 <= landing["score"] <= 100
    assert checks["total"] == 4
