#!/bin/bash
# Simple AIEO test using curl - tests IT-Journey repository

set -e

cd "$(dirname "$0")/../.."

echo "=========================================="
echo "AIEO Test on IT-Journey Repository"
echo "=========================================="
echo ""

# Check if backend is running
echo "Checking backend..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Backend is running"
else
    echo "✗ Backend not running"
    echo ""
    echo "Please start the backend first:"
    echo "  cd backend"
    echo "  source venv/bin/activate"
    echo "  uvicorn app.main:app --reload"
    echo ""
    exit 1
fi

echo ""
echo "=========================================="
echo "Test 1: Auditing IT-Journey README.md"
echo "=========================================="
echo ""

README_PATH="/Users/bamr87/github/it-journey/README.md"

if [ ! -f "$README_PATH" ]; then
    echo "✗ README not found at: $README_PATH"
    exit 1
fi

echo "Reading README from: $README_PATH"
echo "Content length: $(wc -c < "$README_PATH") characters"
echo ""
echo "Sending audit request..."

# Read first 10000 characters to avoid timeout
CONTENT=$(head -c 10000 "$README_PATH")

# Escape for JSON
JSON_CONTENT=$(echo "$CONTENT" | python3 -c "import sys, json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '""')

RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/aieo/audit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-1234567890" \
  -d "{\"content\": $JSON_CONTENT, \"format\": \"markdown\"}")

echo ""
echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

echo ""
echo "=========================================="
echo "Test 2: Auditing IT-Journey Website"
echo "=========================================="
echo ""

echo "Testing website: https://it-journey.dev"
echo "Sending audit request..."

RESPONSE2=$(curl -s -X POST http://localhost:8000/api/v1/aieo/audit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-1234567890" \
  -d '{"url": "https://it-journey.dev"}')

echo ""
echo "Response:"
echo "$RESPONSE2" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE2"

echo ""
echo "=========================================="
echo "Testing Complete!"
echo "=========================================="

