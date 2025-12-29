# AIEO API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" https://api.aieo.dev/v1/aieo/audit
```

## Endpoints

### POST /aieo/audit

Audit content for AIEO score.

**Request:**
```json
{
  "url": "https://example.com/article",
  "content": "# My Article\n...",
  "format": "markdown"
}
```

**Response:**
```json
{
  "score": 67,
  "grade": "C+",
  "gaps": [
    {
      "id": "gap_001",
      "category": "structure",
      "severity": "high",
      "description": "No comparison tables found",
      "location": {"start": 0, "end": 500},
      "example_fix": "Add comparison table for X vs Y"
    }
  ],
  "fixes": [],
  "benchmark": {
    "percentile": 45,
    "engine_scores": {}
  }
}
```

### POST /aieo/optimize

Optimize content with AIEO patterns.

**Request:**
```json
{
  "content": "# My Article\n...",
  "target_engines": ["grok", "claude"],
  "style": "preserve"
}
```

**Response:**
```json
{
  "optimized_content": "# My Article\n\n**Updated December 2025**\n...",
  "score_before": 45,
  "score_after": 78,
  "uplift": 33,
  "changes": [
    {
      "type": "inject",
      "description": "Added temporal anchor",
      "location": {"start": 15, "end": 15},
      "original_text": "",
      "optimized_text": "**Updated December 2025**",
      "expected_uplift": 8
    }
  ]
}
```

### GET /aieo/citations

List citations for URL/domain.

**Query Parameters:**
- `url` (optional): Filter by URL
- `domain` (optional): Filter by domain
- `engine` (optional): Filter by engine
- `limit` (default: 50): Number of results
- `cursor` (optional): Pagination cursor

### GET /aieo/dashboard

Get share-of-voice metrics.

**Response:**
```json
{
  "citation_rate": [],
  "by_engine": {
    "grok": 10,
    "claude": 5
  },
  "top_cited_pages": [
    {
      "url": "https://example.com/article",
      "count": 15
    }
  ]
}
```

### GET /aieo/patterns

Browse pattern library.

**Response:**
```json
{
  "patterns": [
    {
      "id": "structured_data",
      "name": "Structured Data",
      "category": "structure",
      "description": "Convert prose into tables, lists, structured formats",
      "citation_boost": {"min": 15, "max": 25}
    }
  ]
}
```

### POST /aieo/patterns/{pattern_id}/apply

Apply pattern to content.

**Request:**
```json
{
  "content": "# My Article\n..."
}
```

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

**Error Codes:**
- `INVALID_REQUEST`: Missing required fields or invalid format
- `UNAUTHORIZED`: Invalid or missing API key
- `RATE_LIMITED`: Rate limit exceeded
- `NOT_FOUND`: Resource not found
- `CONTENT_TOO_LARGE`: Content exceeds 50,000 word limit
- `FETCH_FAILED`: Unable to fetch URL content
- `INTERNAL_ERROR`: Server error


