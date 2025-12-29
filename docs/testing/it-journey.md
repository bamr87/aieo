# Testing AIEO on IT-Journey

This guide shows how to test the AIEO tool on the it-journey repository and website.

## Prerequisites

1. AIEO backend must be installed and running
2. Docker services (PostgreSQL, Redis, Qdrant) must be running
3. Backend server should be accessible at http://localhost:8000

## Quick Test

### Option 1: Using the Test Script

```bash
# Make sure backend is running first
cd /Users/bamr87/aieo/backend
source venv/bin/activate
uvicorn app.main:app --reload

# In another terminal, run the test
cd /Users/bamr87/aieo
python3 test_api.py
```

### Option 2: Using the CLI

```bash
# Activate backend virtual environment
cd /Users/bamr87/aieo/backend
source venv/bin/activate

# Install CLI if not already installed
cd ../cli
pip install -e .

# Set API key (or use .env)
export AIEO_API_KEY="test-key-1234567890"

# Test 1: Audit IT-Journey README
aieo audit --file /Users/bamr87/github/it-journey/README.md

# Test 2: Audit IT-Journey website
aieo audit https://it-journey.dev

# Test 3: Optimize a sample
aieo optimize /Users/bamr87/github/it-journey/README.md --output /tmp/optimized.md
```

### Option 3: Using curl/HTTP directly

```bash
# Test 1: Audit README content
curl -X POST http://localhost:8000/api/v1/aieo/audit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-1234567890" \
  -d '{
    "content": "# IT-Journey\n\nWelcome to IT-Journey...",
    "format": "markdown"
  }'

# Test 2: Audit website URL
curl -X POST http://localhost:8000/api/v1/aieo/audit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-1234567890" \
  -d '{
    "url": "https://it-journey.dev"
  }'
```

## Expected Results

### README Audit Results

The IT-Journey README should score well because it contains:
- ✅ Structured data (lists, headers)
- ✅ Entity mentions (technologies, tools)
- ✅ Clear sections and organization
- ✅ Links and references

Expected score range: **60-80/100**

Common gaps might include:
- Missing comparison tables
- Could use more temporal anchors (dates)
- Could add FAQ section
- Could improve citation hooks

### Website Audit Results

The it-journey.dev website should score based on:
- HTML structure and semantic markup
- Content organization
- Presence of structured data
- Entity density

Expected score range: **50-70/100** (depends on HTML structure)

## Manual Testing Steps

1. **Start Backend:**
   ```bash
   cd /Users/bamr87/aieo/backend
   source venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. **Start Docker Services:**
   ```bash
   cd /Users/bamr87/aieo
   docker-compose up -d
   ```

3. **Run Audit:**
   ```bash
   # Using Python script
   python3 test_api.py
   
   # Or using CLI
   export AIEO_API_KEY="test-key-1234567890"
   aieo audit --file /Users/bamr87/github/it-journey/README.md
   ```

4. **Check Results:**
   - Score should be between 0-100
   - Grade should be A+, A, B, C, D, or F
   - Gaps should list specific improvements
   - Benchmark should show percentile ranking

## Troubleshooting

### Backend Not Running

```bash
# Check if port 8000 is in use
lsof -i :8000

# Start backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Docker Services Not Running

```bash
# Check status
docker-compose ps

# Start services
docker-compose up -d

# Check logs
docker-compose logs
```

### API Key Issues

The test uses a simple API key validation. For production, you'll need to:
1. Set up proper API key storage in database
2. Implement real authentication
3. Update `.env` with actual keys

### Content Too Large

If the README is too large:
- The API will return a 413 error
- Try testing with a smaller sample
- Or increase `MAX_CONTENT_WORDS` in config

## Sample Test Output

```
AIEO API Test for IT-Journey
==================================================
✓ Backend is running

=== Testing Audit on IT-Journey README ===

✓ Audit successful!
Score: 67/100
Grade: C+

Top 5 Gaps:
  1. [comparison] No comparison tables found
     Severity: high
  2. [temporal] Missing temporal anchors (dates, versions)
     Severity: medium
  3. [faq] Missing FAQ section
     Severity: medium
  4. [citations] Missing citation hooks
     Severity: medium
  5. [recursion] Missing recursive depth (nested Q&A)
     Severity: high

=== Testing Audit on IT-Journey Website ===

✓ Audit successful!
Score: 58/100
Grade: D

Top 5 Gaps:
  1. [structure] Missing structured data (tables, lists)
     Severity: high
  2. [entities] Low entity density
     Severity: medium
  ...

==================================================
Testing complete!
```

## Next Steps

After testing:
1. Review the gaps identified
2. Use `aieo optimize` to generate optimized versions
3. Compare before/after scores
4. Apply optimizations to improve citation likelihood


