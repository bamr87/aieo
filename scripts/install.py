#!/usr/bin/env python3
"""
AIEO Installation and Configuration Script (Cross-platform)
This script sets up the AIEO development environment
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 40}{Colors.NC}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓{Colors.NC} {text}")

def print_error(text):
    print(f"{Colors.RED}✗{Colors.NC} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠{Colors.NC} {text}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ{Colors.NC} {text}")

def command_exists(command):
    """Check if a command exists in PATH"""
    return shutil.which(command) is not None

def run_command(cmd, check=True, capture_output=False, cwd=None):
    """Run a shell command"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=capture_output,
            text=True,
            cwd=cwd
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e

def check_prerequisites():
    """Check if all required tools are installed"""
    print_header("Checking Prerequisites")
    
    missing = []
    
    # Check Python
    if not command_exists("python3"):
        print_error("Python 3 is not installed")
        missing.append("python3")
    else:
        version = run_command("python3 --version", capture_output=True).stdout.strip()
        print_success(f"{version} found")
    
    # Check Node.js
    if not command_exists("node"):
        print_error("Node.js is not installed")
        missing.append("node")
    else:
        version = run_command("node --version", capture_output=True).stdout.strip()
        print_success(f"{version} found")
    
    # Check npm
    if not command_exists("npm"):
        print_error("npm is not installed")
        missing.append("npm")
    else:
        version = run_command("npm --version", capture_output=True).stdout.strip()
        print_success(f"npm {version} found")
    
    # Check Docker
    if not command_exists("docker"):
        print_error("Docker is not installed")
        print_info("Please install Docker from https://www.docker.com/get-started")
        missing.append("docker")
    else:
        version = run_command("docker --version", capture_output=True).stdout.strip()
        print_success(f"{version} found")
    
    # Check docker-compose
    docker_compose_cmd = "docker-compose"
    if not command_exists(docker_compose_cmd):
        # Try docker compose (v2)
        if command_exists("docker") and run_command("docker compose version", check=False).returncode == 0:
            docker_compose_cmd = "docker compose"
            print_success("docker compose (v2) found")
        else:
            print_error("docker-compose is not installed")
            missing.append("docker-compose")
    else:
        version = run_command(f"{docker_compose_cmd} --version", capture_output=True).stdout.strip()
        print_success(f"{version} found")
    
    if missing:
        print_error(f"Missing prerequisites: {', '.join(missing)}")
        print_info("Please install them and run this script again.")
        sys.exit(1)
    
    print_success("All prerequisites met!")
    return docker_compose_cmd

def setup_backend():
    """Setup Python backend"""
    print_header("Setting Up Backend")
    
    backend_dir = Path("backend")
    venv_dir = backend_dir / "venv"
    
    # Create virtual environment
    if not venv_dir.exists():
        print_info("Creating Python virtual environment...")
        run_command("python3 -m venv venv", cwd=backend_dir)
        print_success("Virtual environment created")
    else:
        print_info("Virtual environment already exists")
    
    # Determine activation script
    if sys.platform == "win32":
        activate_script = venv_dir / "Scripts" / "activate.bat"
        pip_cmd = str(venv_dir / "Scripts" / "pip")
        python_cmd = str(venv_dir / "Scripts" / "python")
    else:
        activate_script = venv_dir / "bin" / "activate"
        pip_cmd = str(venv_dir / "bin" / "pip")
        python_cmd = str(venv_dir / "bin" / "python")
    
    # Upgrade pip
    print_info("Upgrading pip...")
    run_command(f"{pip_cmd} install --upgrade pip", check=False)
    
    # Install dependencies
    print_info("Installing Python dependencies...")
    run_command(f"{pip_cmd} install -r requirements.txt", cwd=backend_dir)
    
    print_success("Backend dependencies installed")
    return python_cmd, pip_cmd

def setup_frontend():
    """Setup React frontend"""
    print_header("Setting Up Frontend")
    
    frontend_dir = Path("frontend")
    
    print_info("Installing Node.js dependencies...")
    run_command("npm install", cwd=frontend_dir)
    
    print_success("Frontend dependencies installed")

def setup_cli(pip_cmd):
    """Setup CLI tool"""
    print_header("Setting Up CLI")
    
    cli_dir = Path("cli")
    
    print_info("Installing CLI dependencies...")
    run_command(f"{pip_cmd} install -r requirements.txt", cwd=cli_dir)
    
    print_info("Installing CLI package...")
    run_command(f"{pip_cmd} install -e .", cwd=cli_dir)
    
    print_success("CLI installed")

def setup_env():
    """Setup environment configuration"""
    print_header("Setting Up Environment Configuration")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print_success("Created .env file from env.example")
            print_warning("Please edit .env file and add your API keys:")
            print_info("  - OPENAI_API_KEY")
            print_info("  - ANTHROPIC_API_KEY (optional)")
        else:
            print_error("env.example file not found")
    else:
        print_info(".env file already exists, skipping...")

def setup_database(docker_compose_cmd, python_cmd):
    """Setup database and run migrations"""
    print_header("Setting Up Database")
    
    # Start Docker services
    print_info("Starting Docker services (PostgreSQL, Redis, Qdrant)...")
    run_command(f"{docker_compose_cmd} up -d")
    
    # Wait for services
    print_info("Waiting for services to be ready...")
    time.sleep(5)
    
    # Check services
    result = run_command(f"{docker_compose_cmd} ps", capture_output=True)
    if "Up" in result.stdout:
        print_success("Docker services started")
    else:
        print_error("Failed to start Docker services")
        sys.exit(1)
    
    # Run migrations
    print_info("Running database migrations...")
    backend_dir = Path("backend")
    
    # Wait a bit more for PostgreSQL
    time.sleep(3)
    
    # Try migrations
    alembic_cmd = str(Path(python_cmd).parent / "alembic")
    result = run_command(
        f"{alembic_cmd} upgrade head",
        cwd=backend_dir,
        check=False
    )
    
    if result.returncode == 0:
        print_success("Database migrations completed")
    else:
        print_warning("Database migrations failed (this is OK if TimescaleDB extension is not available)")
        print_info("You can run migrations manually later with:")
        print_info(f"  cd backend && {python_cmd} -m alembic upgrade head")

def setup_spacy(python_cmd):
    """Download spaCy model"""
    print_header("Setting Up spaCy Model")
    
    print_info("Downloading spaCy English model (this may take a few minutes)...")
    result = run_command(
        f"{python_cmd} -m spacy download en_core_web_sm",
        check=False
    )
    
    if result.returncode == 0:
        print_success("spaCy model downloaded")
    else:
        print_warning("Failed to download spaCy model automatically")
        print_info("You can download it manually with:")
        print_info(f"  {python_cmd} -m spacy download en_core_web_sm")

def main():
    """Main installation function"""
    print(f"{Colors.GREEN}")
    print("╔════════════════════════════════════════╗")
    print("║   AIEO Installation Script           ║")
    print("║   AI Engine Optimization Platform    ║")
    print("╚════════════════════════════════════════╝")
    print(f"{Colors.NC}")
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Check prerequisites
    docker_compose_cmd = check_prerequisites()
    
    # Setup components
    python_cmd, pip_cmd = setup_backend()
    setup_frontend()
    setup_cli(pip_cmd)
    setup_env()
    setup_database(docker_compose_cmd, python_cmd)
    setup_spacy(python_cmd)
    
    # Final instructions
    print_header("Installation Complete!")
    
    print(f"{Colors.GREEN}Next steps:{Colors.NC}")
    print("")
    print("1. Edit .env file and add your API keys:")
    print("   - OPENAI_API_KEY (required for optimization)")
    print("   - ANTHROPIC_API_KEY (optional)")
    print("")
    
    if sys.platform == "win32":
        print("2. Start the backend server:")
        print("   cd backend")
        print("   venv\\Scripts\\activate")
        print("   python -m uvicorn app.main:app --reload")
    else:
        print("2. Start the backend server:")
        print("   cd backend")
        print("   source venv/bin/activate")
        print("   uvicorn app.main:app --reload")
    
    print("")
    print("3. Start the frontend (in a new terminal):")
    print("   cd frontend")
    print("   npm run dev")
    print("")
    print("4. Access the application:")
    print("   - Web UI: http://localhost:5173")
    print("   - API Docs: http://localhost:8000/docs")
    print("")
    print("5. Use the CLI:")
    print("   aieo audit https://example.com/article")
    print("   aieo optimize article.md")
    print("")
    print(f"{Colors.YELLOW}Note: Make sure Docker services are running:{Colors.NC}")
    print(f"   {docker_compose_cmd} ps")
    print(f"   {docker_compose_cmd} up -d  # if not running")
    print("")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Installation failed: {e}")
        sys.exit(1)


