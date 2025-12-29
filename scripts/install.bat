@echo off
REM AIEO Installation Script for Windows
REM This script sets up the AIEO development environment on Windows

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   AIEO Installation Script
echo   AI Engine Optimization Platform
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    exit /b 1
) else (
    echo [OK] Python found
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed
    echo Please install Node.js from https://nodejs.org/
    exit /b 1
) else (
    echo [OK] Node.js found
)

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed
    echo Please install Docker Desktop from https://www.docker.com/get-started
    exit /b 1
) else (
    echo [OK] Docker found
)

echo.
echo [INFO] Starting installation...
echo.

REM Setup backend
echo [INFO] Setting up backend...
cd backend
if not exist venv (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies
    exit /b 1
)
echo [OK] Backend dependencies installed
cd ..

REM Setup frontend
echo [INFO] Setting up frontend...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install frontend dependencies
    exit /b 1
)
echo [OK] Frontend dependencies installed
cd ..

REM Setup CLI
echo [INFO] Setting up CLI...
cd cli
call ..\backend\venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -e .
if errorlevel 1 (
    echo [ERROR] Failed to install CLI
    exit /b 1
)
echo [OK] CLI installed
cd ..

REM Setup environment
echo [INFO] Setting up environment configuration...
if not exist .env (
    if exist env.example (
        copy env.example .env >nul
        echo [OK] Created .env file from env.example
        echo [WARNING] Please edit .env file and add your API keys
    ) else (
        echo [ERROR] env.example file not found
    )
) else (
    echo [INFO] .env file already exists
)

REM Setup Docker services
echo [INFO] Starting Docker services...
docker-compose up -d
if errorlevel 1 (
    echo [ERROR] Failed to start Docker services
    exit /b 1
)
echo [INFO] Waiting for services to be ready...
timeout /t 5 /nobreak >nul
echo [OK] Docker services started

REM Run migrations
echo [INFO] Running database migrations...
cd backend
call venv\Scripts\activate.bat
timeout /t 3 /nobreak >nul
alembic upgrade head
if errorlevel 1 (
    echo [WARNING] Database migrations failed (this is OK if TimescaleDB extension is not available)
    echo [INFO] You can run migrations manually later
)
cd ..

REM Download spaCy model
echo [INFO] Downloading spaCy model...
cd backend
call venv\Scripts\activate.bat
python -m spacy download en_core_web_sm
if errorlevel 1 (
    echo [WARNING] Failed to download spaCy model automatically
    echo [INFO] You can download it manually later
)
cd ..

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Next steps:
echo.
echo 1. Edit .env file and add your API keys:
echo    - OPENAI_API_KEY (required)
echo    - ANTHROPIC_API_KEY (optional)
echo.
echo 2. Start the backend server:
echo    cd backend
echo    venv\Scripts\activate
echo    uvicorn app.main:app --reload
echo.
echo 3. Start the frontend (in a new terminal):
echo    cd frontend
echo    npm run dev
echo.
echo 4. Access the application:
echo    - Web UI: http://localhost:5173
echo    - API Docs: http://localhost:8000/docs
echo.
echo 5. Use the CLI:
echo    aieo audit https://example.com/article
echo    aieo optimize article.md
echo.

endlocal


