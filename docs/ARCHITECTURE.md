# AIEO Architecture

## Overview

AIEO is a full-stack application for optimizing content to maximize AI engine citations. It consists of a FastAPI backend, React frontend, and Python CLI tool.

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│    Backend   │────▶│  Database   │
│   (React)   │     │   (FastAPI)  │     │ (PostgreSQL)│
└─────────────┘     └──────────────┘     └─────────────┘
                            │
                            ├────▶ Redis (Cache)
                            ├────▶ Qdrant (Vectors)
                            └────▶ AI Services (OpenAI/Anthropic)
```

## Components

### Backend (`backend/`)

**Framework:** FastAPI (Python 3.9+)

**Structure:**
```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   │   ├── audit.py     # Content auditing
│   │   ├── optimize.py  # Content optimization
│   │   ├── citations.py # Citation tracking
│   │   └── patterns.py  # Pattern library
│   ├── core/            # Core utilities
│   │   ├── config.py    # Configuration
│   │   ├── database.py  # Database connection
│   │   ├── security.py  # Authentication
│   │   └── validation.py # Input validation
│   ├── models/          # Database models
│   ├── services/        # Business logic
│   │   ├── scoring_engine.py
│   │   ├── content_parser.py
│   │   ├── audit_service.py
│   │   └── optimize_service.py
│   └── tasks/           # Celery tasks
└── tests/               # Test suite
```

**Key Services:**

1. **Scoring Engine** (`scoring_engine.py`)
   - Detects 10 AIEO patterns with weighted scoring (total: 125 max raw → normalized to 100)
   - Calculates composite score (0-100) and letter grade
   - Identifies gaps (missing patterns) sorted by severity
   - Detects anti-patterns (over-optimization, keyword stuffing, missing structure) and applies penalties
   - Can run standalone without any external services (except optional spaCy for entity density)

2. **Content Parser** (`content_parser.py`)
   - Parses markdown and HTML via `markdown` + `beautifulsoup4`
   - Extracts: headers, tables, lists, links, word count, content hash
   - HTML-to-markdown conversion via `html2text` for URL-fetched content
   - No external service dependencies

3. **Audit Service** (`audit_service.py`)
   - Orchestrates content analysis (URL fetching → parsing → scoring → benchmarking)
   - Redis-based caching (content hash as cache key)
   - Generates audit reports with benchmark percentiles
   - Requires full backend stack (Redis, PostgreSQL, Qdrant)

4. **Optimize Service** (`optimize_service.py`)
   - Applies AIEO patterns via AI (OpenAI GPT-4 or Anthropic Claude)
   - Uses AI for content optimization
   - Generates change recommendations

### Frontend (`frontend/`)

**Framework:** React + TypeScript + Vite

**Structure:**
```
frontend/
├── src/
│   ├── pages/           # Page components
│   │   ├── AuditPage.tsx
│   │   ├── OptimizePage.tsx
│   │   └── DashboardPage.tsx
│   ├── components/      # Reusable components
│   ├── services/        # API client
│   └── App.tsx          # Main app component
└── public/              # Static assets
```

**Features:**
- Content auditing interface
- Optimization interface
- Dashboard for metrics
- Pattern library browser

### CLI (`cli/`)

**Framework:** Python Click

**Commands:**
- `aieo audit` - Audit content
- `aieo optimize` - Optimize content
- `aieo dashboard` - View metrics

## Operational Modes

### Full Stack Mode (API + Services)

Requires: PostgreSQL, Redis, Docker (optional: Qdrant, OpenAI/Anthropic)

All features available: API endpoints, caching, optimization, citation tracking, benchmarking.

### Standalone Mode (Scoring Engine Only)

Requires: `httpx`, `beautifulsoup4`, `markdown`, `html2text` (optional: `spacy`)

The `run_audit.py` script uses the scoring engine directly, bypassing the API stack. This is ideal for batch auditing URLs without running infrastructure services. The script:

1. Reads URLs from `sites.txt`
2. Fetches HTML content via `httpx`
3. Passes content through `ContentParser` (HTML → structured data)
4. Scores against all 10 AIEO patterns via `ScoringEngine`
5. Outputs per-site JSON + summary to a temp directory

**Limitations of standalone mode:**
- No caching (each run re-fetches and re-scores)
- No AI-powered optimization (requires OpenAI/Anthropic keys + API)
- No benchmark percentile (requires Qdrant vector DB)
- No citation tracking
- Entity density scoring requires separate `spacy` + `en_core_web_sm` install

## Data Flow

### Audit Flow

```
User Input (URL/Content)
    ↓
Content Parser (extract structure)
    ↓
Scoring Engine (detect patterns)
    ↓
Gap Analysis (identify improvements)
    ↓
Benchmark Comparison (percentile ranking)   ← skipped in standalone mode
    ↓
Audit Result (score + recommendations)
```

### Optimization Flow

```
Original Content
    ↓
Audit (identify gaps)
    ↓
AI Service (apply patterns)
    ↓
Optimized Content
    ↓
Re-score (measure improvement)
    ↓
Optimization Result (before/after + changes)
```

## Database Schema

### Tables

1. **users**
   - User accounts and settings

2. **api_keys**
   - API key management
   - Usage tracking

3. **audits**
   - Audit history
   - Score tracking

4. **citations**
   - Citation records (TimescaleDB hypertable)
   - Time-series data

## External Services

### Required

- **PostgreSQL** - Primary database
- **Redis** - Caching and Celery broker

### Optional

- **Qdrant** - Vector database for benchmarks
- **OpenAI** - Content optimization
- **Anthropic** - Alternative optimization provider

## Security

### Authentication
- API key authentication
- Key hashing (SHA256)
- Rate limiting

### Data Protection
- Input validation
- Content sanitization
- SQL injection prevention
- XSS prevention

### Privacy
- User-controlled data retention
- Encrypted storage
- TLS encryption in transit

## Deployment

### Development
- Docker Compose for local services
- Hot reload for development
- Local database

### Production
- Containerized services
- Environment-based configuration
- Health checks
- Monitoring and logging

## Performance

### Targets
- Audit response: <15 seconds
- API response: P99 < 15 seconds
- Parsing: <100ms for typical content

### Optimization
- Redis caching
- Database indexing
- Async processing (Celery)
- Connection pooling

## Scalability

### Horizontal Scaling
- Stateless API servers
- Load balancer support
- Database replication

### Vertical Scaling
- Connection pooling
- Caching strategies
- Query optimization

## Monitoring

### Metrics
- Request latency
- Error rates
- Cache hit rates
- Database query performance

### Logging
- Structured logging
- Request/response logging
- Error tracking

## Future Architecture

### Planned Improvements
- Microservices architecture (if needed)
- Event-driven architecture for citations
- GraphQL API option
- Real-time updates via WebSockets

See [PRD-aieo.md](../PRD-aieo.md) for detailed roadmap.

