# AIEO Installation Guide

This guide will help you set up the AIEO development environment.

## Quick Start

### Option 1: Automated Installation (Recommended)

**Linux/macOS:**
```bash
./scripts/install.sh
```

**Windows:**
```bash
python scripts/install.py
```

**Cross-platform:**
```bash
python3 scripts/install.py
```

The installation script will:
- Check prerequisites
- Set up Python backend with virtual environment
- Set up React frontend
- Set up CLI tool
- Create `.env` file from template
- Start Docker services (PostgreSQL, Redis, Qdrant)
- Run database migrations
- Download spaCy model

### Option 2: Manual Installation

If you prefer to set up manually, follow these steps:

## Prerequisites

- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Docker** - [Download](https://www.docker.com/get-started)
- **docker-compose** - Usually included with Docker Desktop

Verify installations:
```bash
python3 --version
node --version
npm --version
docker --version
docker-compose --version
```

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd aieo
```

### 2. Set Up Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

cd ..
```

### 3. Set Up Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Set Up CLI

```bash
cd cli

# Activate backend virtual environment first
source ../backend/venv/bin/activate  # Linux/macOS
# OR
../backend/venv/Scripts/activate  # Windows

# Install CLI dependencies
pip install -r requirements.txt

# Install CLI package
pip install -e .

cd ..
```

### 5. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env and add your API keys
# Required:
# - OPENAI_API_KEY=your-openai-api-key
# Optional:
# - ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 6. Start Docker Services

```bash
# Start PostgreSQL, Redis, and Qdrant
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 7. Run Database Migrations

```bash
cd backend
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows

# Run migrations
alembic upgrade head

cd ..
```

## Running the Application

### Start Backend Server

```bash
cd backend
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows

uvicorn app.main:app --reload
```

Backend will be available at: http://localhost:8000
API documentation: http://localhost:8000/docs

### Start Frontend (in a new terminal)

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:5173

### Use CLI Tool

```bash
# Make sure backend virtual environment is activated
source backend/venv/bin/activate  # Linux/macOS

# Set API key (optional, can also use .env)
export AIEO_API_KEY=your-api-key

# Audit content
aieo audit https://example.com/article
aieo audit --file article.md

# Optimize content
aieo optimize article.md --output optimized.md

# View dashboard
aieo dashboard
```

## Troubleshooting

### Docker Services Not Starting

```bash
# Check Docker is running
docker ps

# Restart services
docker-compose down
docker-compose up -d

# View logs
docker-compose logs
```

### Database Connection Issues

```bash
# Wait for PostgreSQL to be ready (may take 30-60 seconds)
docker-compose logs postgres

# Check if TimescaleDB extension is available
docker-compose exec postgres psql -U aieo -d aieo -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

### Python Virtual Environment Issues

```bash
# Recreate virtual environment
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### spaCy Model Not Found

```bash
cd backend
source venv/bin/activate
python -m spacy download en_core_web_sm
```

### Port Already in Use

If ports 8000, 5173, 5432, 6379, or 6333 are already in use:

1. Stop the conflicting service
2. Or modify ports in:
   - `docker-compose.yml` (for database services)
   - `backend/app/core/config.py` (for API port)
   - `frontend/vite.config.ts` (for frontend port)

## Development Commands

```bash
# Run tests
cd backend
source venv/bin/activate
pytest

# Format code
make format

# Lint code
make lint

# View Docker logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Next Steps

1. **Get API Keys:**
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/

2. **Read Documentation:**
   - [API Documentation](docs/API.md)
   - [CLI Documentation](docs/CLI.md)
   - [Pattern Library](docs/PATTERNS.md)

3. **Start Developing:**
   - Check out the [README](README.md) for project structure
   - Review the [PRD](PRD-aieo.md) for product requirements

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Docker logs: `docker-compose logs`
3. Check backend logs in the terminal running `uvicorn`
4. Verify all prerequisites are installed correctly


