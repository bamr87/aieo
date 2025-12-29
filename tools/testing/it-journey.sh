#!/bin/bash

# Test AIEO on it-journey repository
# This script tests the AIEO tool on the it-journey README and website

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Change to AIEO root directory (go up from tools/testing)
cd "$(dirname "$0")/../.."

print_header "Testing AIEO on IT-Journey"

# Check if backend is running
print_info "Checking if backend is running..."
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    print_success "Backend is running"
else
    print_error "Backend is not running"
    print_info "Starting backend..."
    
    # Try to start backend
    cd backend
    if [ -d "venv" ]; then
        source venv/bin/activate
        print_info "Starting backend server in background..."
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 >/tmp/aieo_backend.log 2>&1 &
        BACKEND_PID=$!
        echo $BACKEND_PID > /tmp/aieo_backend.pid
        sleep 3
        
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            print_success "Backend started successfully"
        else
            print_error "Failed to start backend. Check /tmp/aieo_backend.log"
            exit 1
        fi
    else
        print_error "Backend venv not found. Please run ./scripts/install.sh first"
        exit 1
    fi
    cd ..
fi

# Check if CLI is available
print_info "Checking CLI availability..."
if command -v aieo >/dev/null 2>&1; then
    print_success "CLI is available"
else
    print_info "CLI not in PATH, using direct Python execution..."
    CLI_CMD="cd cli && python -m aieo.cli"
else
    CLI_CMD="aieo"
fi

# Test 1: Audit it-journey README.md
print_header "Test 1: Auditing IT-Journey README.md"

README_PATH="/Users/bamr87/github/it-journey/README.md"

if [ -f "$README_PATH" ]; then
    print_info "Found README at: $README_PATH"
    
    if command -v aieo >/dev/null 2>&1; then
        aieo audit --file "$README_PATH" || {
            print_error "Audit failed, trying with API key..."
            export AIEO_API_KEY="test-key-1234567890"
            aieo audit --file "$README_PATH"
        }
    else
        cd cli
        source ../backend/venv/bin/activate
        export AIEO_API_KEY="test-key-1234567890"
        python -m aieo.cli audit --file "$README_PATH"
        cd ..
    fi
else
    print_error "README not found at: $README_PATH"
fi

# Test 2: Audit it-journey.dev website
print_header "Test 2: Auditing IT-Journey Website (it-journey.dev)"

if command -v aieo >/dev/null 2>&1; then
    aieo audit https://it-journey.dev || {
        print_error "Audit failed, trying with API key..."
        export AIEO_API_KEY="test-key-1234567890"
        aieo audit https://it-journey.dev
    }
else
    cd cli
    source ../backend/venv/bin/activate
    export AIEO_API_KEY="test-key-1234567890"
    python -m aieo.cli audit https://it-journey.dev
    cd ..
fi

# Test 3: Optimize a sample from README
print_header "Test 3: Testing Optimization on README Sample"

# Extract a sample section
SAMPLE_CONTENT=$(head -100 "$README_PATH" | tail -50)

if [ -n "$SAMPLE_CONTENT" ]; then
    # Create temp file
    TEMP_FILE=$(mktemp)
    echo "$SAMPLE_CONTENT" > "$TEMP_FILE"
    
    print_info "Optimizing sample content..."
    
    if command -v aieo >/dev/null 2>&1; then
        aieo optimize "$TEMP_FILE" --output "${TEMP_FILE}.optimized" || {
            export AIEO_API_KEY="test-key-1234567890"
            aieo optimize "$TEMP_FILE" --output "${TEMP_FILE}.optimized"
        }
    else
        cd cli
        source ../backend/venv/bin/activate
        export AIEO_API_KEY="test-key-1234567890"
        python -m aieo.cli optimize "$TEMP_FILE" --output "${TEMP_FILE}.optimized"
        cd ..
    fi
    
    if [ -f "${TEMP_FILE}.optimized" ]; then
        print_success "Optimization completed"
        print_info "Optimized content saved to: ${TEMP_FILE}.optimized"
        echo ""
        echo "First 20 lines of optimized content:"
        head -20 "${TEMP_FILE}.optimized"
    fi
    
    # Cleanup
    rm -f "$TEMP_FILE" "${TEMP_FILE}.optimized"
fi

print_header "Testing Complete!"

# Cleanup: Stop backend if we started it
if [ -f /tmp/aieo_backend.pid ]; then
    BACKEND_PID=$(cat /tmp/aieo_backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        print_info "Stopping backend server..."
        kill $BACKEND_PID
        rm /tmp/aieo_backend.pid
    fi
fi


