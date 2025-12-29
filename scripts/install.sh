#!/bin/bash

# AIEO Installation and Configuration Script
# This script sets up the AIEO development environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local missing=0
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        missing=1
    else
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION found"
    fi
    
    if ! command_exists node; then
        print_error "Node.js is not installed"
        missing=1
    else
        NODE_VERSION=$(node --version)
        print_success "Node.js $NODE_VERSION found"
    fi
    
    if ! command_exists npm; then
        print_error "npm is not installed"
        missing=1
    else
        NPM_VERSION=$(npm --version)
        print_success "npm $NPM_VERSION found"
    fi
    
    if ! command_exists docker; then
        print_error "Docker is not installed"
        print_info "Please install Docker from https://www.docker.com/get-started"
        missing=1
    else
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        print_success "Docker $DOCKER_VERSION found"
    fi
    
    if ! command_exists docker-compose; then
        print_error "docker-compose is not installed"
        print_info "Please install docker-compose"
        missing=1
    else
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | tr -d ',')
        print_success "docker-compose $COMPOSE_VERSION found"
    fi
    
    if [ $missing -eq 1 ]; then
        print_error "Some prerequisites are missing. Please install them and run this script again."
        exit 1
    fi
    
    print_success "All prerequisites met!"
}

# Setup backend
setup_backend() {
    print_header "Setting Up Backend"
    
    cd backend
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1
    
    # Install dependencies
    print_info "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_success "Backend dependencies installed"
    
    cd ..
}

# Setup frontend
setup_frontend() {
    print_header "Setting Up Frontend"
    
    cd frontend
    
    # Install dependencies
    print_info "Installing Node.js dependencies..."
    npm install
    
    print_success "Frontend dependencies installed"
    
    cd ..
}

# Setup CLI
setup_cli() {
    print_header "Setting Up CLI"
    
    cd cli
    
    # Install dependencies
    print_info "Installing CLI dependencies..."
    pip install -r requirements.txt
    
    # Install CLI package
    print_info "Installing CLI package..."
    pip install -e .
    
    print_success "CLI installed"
    
    cd ..
}

# Setup environment file
setup_env() {
    print_header "Setting Up Environment Configuration"
    
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            cp env.example .env
            print_success "Created .env file from env.example"
            print_warning "Please edit .env file and add your API keys:"
            print_info "  - OPENAI_API_KEY"
            print_info "  - ANTHROPIC_API_KEY (optional)"
        else
            print_error "env.example file not found"
        fi
    else
        print_info ".env file already exists, skipping..."
    fi
}

# Setup database
setup_database() {
    print_header "Setting Up Database"
    
    # Start Docker services
    print_info "Starting Docker services (PostgreSQL, Redis, Qdrant)..."
    docker-compose up -d
    
    # Wait for services to be ready
    print_info "Waiting for services to be ready..."
    sleep 5
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Docker services started"
    else
        print_error "Failed to start Docker services"
        exit 1
    fi
    
    # Run migrations
    print_info "Running database migrations..."
    cd backend
    source venv/bin/activate
    
    # Wait a bit more for PostgreSQL to be fully ready
    sleep 3
    
    # Try to run migrations (may fail if TimescaleDB extension not available, that's OK for MVP)
    if alembic upgrade head 2>/dev/null; then
        print_success "Database migrations completed"
    else
        print_warning "Database migrations failed (this is OK if TimescaleDB extension is not available)"
        print_info "You can run migrations manually later with: cd backend && source venv/bin/activate && alembic upgrade head"
    fi
    
    cd ..
}

# Download spaCy model
setup_spacy() {
    print_header "Setting Up spaCy Model"
    
    cd backend
    source venv/bin/activate
    
    print_info "Downloading spaCy English model (this may take a few minutes)..."
    if python -m spacy download en_core_web_sm 2>/dev/null; then
        print_success "spaCy model downloaded"
    else
        print_warning "Failed to download spaCy model automatically"
        print_info "You can download it manually with: python -m spacy download en_core_web_sm"
    fi
    
    cd ..
}

# Main installation
main() {
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════╗"
    echo "║   AIEO Installation Script           ║"
    echo "║   AI Engine Optimization Platform    ║"
    echo "╚════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Check prerequisites
    check_prerequisites
    
    # Setup components
    setup_backend
    setup_frontend
    setup_cli
    setup_env
    setup_database
    setup_spacy
    
    # Final instructions
    print_header "Installation Complete!"
    
    echo -e "${GREEN}Next steps:${NC}"
    echo ""
    echo "1. Edit .env file and add your API keys:"
    echo "   - OPENAI_API_KEY (required for optimization)"
    echo "   - ANTHROPIC_API_KEY (optional)"
    echo ""
    echo "2. Start the backend server:"
    echo "   cd backend"
    echo "   source venv/bin/activate"
    echo "   uvicorn app.main:app --reload"
    echo ""
    echo "3. Start the frontend (in a new terminal):"
    echo "   cd frontend"
    echo "   npm run dev"
    echo ""
    echo "4. Access the application:"
    echo "   - Web UI: http://localhost:5173"
    echo "   - API Docs: http://localhost:8000/docs"
    echo ""
    echo "5. Use the CLI:"
    echo "   aieo audit https://example.com/article"
    echo "   aieo optimize article.md"
    echo ""
    echo -e "${YELLOW}Note: Make sure Docker services are running:${NC}"
    echo "   docker-compose ps"
    echo "   docker-compose up -d  # if not running"
    echo ""
}

# Run main function
main


