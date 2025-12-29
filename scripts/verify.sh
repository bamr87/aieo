#!/bin/bash

# AIEO Verification Script
# Checks if the installation is complete and working

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

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

errors=0
warnings=0

print_header "AIEO Installation Verification"

# Check backend
echo "Checking backend..."
if [ -d "backend/venv" ]; then
    print_success "Backend virtual environment exists"
else
    print_error "Backend virtual environment not found"
    errors=$((errors + 1))
fi

if [ -f "backend/requirements.txt" ]; then
    print_success "Backend requirements.txt found"
else
    print_error "Backend requirements.txt not found"
    errors=$((errors + 1))
fi

# Check frontend
echo "Checking frontend..."
if [ -d "frontend/node_modules" ]; then
    print_success "Frontend node_modules exists"
else
    print_warning "Frontend node_modules not found (run: cd frontend && npm install)"
    warnings=$((warnings + 1))
fi

if [ -f "frontend/package.json" ]; then
    print_success "Frontend package.json found"
else
    print_error "Frontend package.json not found"
    errors=$((errors + 1))
fi

# Check CLI
echo "Checking CLI..."
if [ -d "cli" ]; then
    print_success "CLI directory exists"
else
    print_error "CLI directory not found"
    errors=$((errors + 1))
fi

# Check environment
echo "Checking environment..."
if [ -f ".env" ]; then
    print_success ".env file exists"
    
    # Check for API keys
    if grep -q "OPENAI_API_KEY=your-openai-api-key-here" .env 2>/dev/null || ! grep -q "OPENAI_API_KEY=" .env 2>/dev/null; then
        print_warning "OPENAI_API_KEY not configured in .env"
        warnings=$((warnings + 1))
    else
        print_success "OPENAI_API_KEY configured"
    fi
else
    print_warning ".env file not found (copy from env.example)"
    warnings=$((warnings + 1))
fi

# Check Docker services
echo "Checking Docker services..."
if command -v docker-compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1; then
    print_success "docker-compose available"
    
    # Check if services are running
    if docker-compose ps 2>/dev/null | grep -q "Up" || docker compose ps 2>/dev/null | grep -q "Up"; then
        print_success "Docker services are running"
    else
        print_warning "Docker services not running (run: docker-compose up -d)"
        warnings=$((warnings + 1))
    fi
else
    print_error "docker-compose not found"
    errors=$((errors + 1))
fi

# Check spaCy model
echo "Checking spaCy model..."
if [ -d "backend/venv" ]; then
    source backend/venv/bin/activate 2>/dev/null || true
    if python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null; then
        print_success "spaCy model installed"
    else
        print_warning "spaCy model not found (run: python -m spacy download en_core_web_sm)"
        warnings=$((warnings + 1))
    fi
    deactivate 2>/dev/null || true
fi

# Summary
print_header "Verification Summary"

if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    print_success "All checks passed! Installation looks good."
    exit 0
elif [ $errors -eq 0 ]; then
    print_warning "Installation complete with $warnings warning(s)"
    print_info "Review warnings above and fix if needed"
    exit 0
else
    print_error "Installation incomplete: $errors error(s), $warnings warning(s)"
    print_info "Please fix errors and run installation script again"
    exit 1
fi


