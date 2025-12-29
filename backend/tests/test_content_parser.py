"""Tests for content parser."""
import pytest
from app.services.content_parser import ContentParser


def test_parse_markdown():
    """Test parsing markdown content."""
    parser = ContentParser()
    content = "# Title\n\nSome text here."
    
    result = parser.parse(content, format="markdown")
    
    assert "text" in result
    assert "headers" in result
    assert "tables" in result
    assert "lists" in result
    assert len(result["headers"]) > 0


def test_parse_html():
    """Test parsing HTML content."""
    parser = ContentParser()
    content = "<h1>Title</h1><p>Some text</p>"
    
    result = parser.parse(content, format="html")
    
    assert "text" in result
    assert len(result["headers"]) > 0


def test_extract_tables():
    """Test table extraction."""
    parser = ContentParser()
    content = """# Test

| Col1 | Col2 |
|------|------|
| Val1 | Val2 |
"""
    
    result = parser.parse(content)
    
    assert len(result["tables"]) > 0
    assert result["tables"][0]["row_count"] > 0


