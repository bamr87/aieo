#!/usr/bin/env python3
"""
AIEO Verification Script (Cross-platform)
Checks if the installation is complete and working
"""

import os
import sys
import subprocess
from pathlib import Path

# Colors
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

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

def run_command(cmd, check=False):
    """Run a command and return success status"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def check_file(path):
    """Check if file exists"""
    return Path(path).exists()

def check_dir(path):
    """Check if directory exists"""
    return Path(path).is_dir()

def main():
    errors = 0
    warnings = 0
    
    print_header("AIEO Installation Verification")
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Check backend
    print("Checking backend...")
    if check_dir("backend/venv"):
        print_success("Backend virtual environment exists")
    else:
        print_error("Backend virtual environment not found")
        errors += 1
    
    if check_file("backend/requirements.txt"):
        print_success("Backend requirements.txt found")
    else:
        print_error("Backend requirements.txt not found")
        errors += 1
    
    # Check frontend
    print("Checking frontend...")
    if check_dir("frontend/node_modules"):
        print_success("Frontend node_modules exists")
    else:
        print_warning("Frontend node_modules not found (run: cd frontend && npm install)")
        warnings += 1
    
    if check_file("frontend/package.json"):
        print_success("Frontend package.json found")
    else:
        print_error("Frontend package.json not found")
        errors += 1
    
    # Check CLI
    print("Checking CLI...")
    if check_dir("cli"):
        print_success("CLI directory exists")
    else:
        print_error("CLI directory not found")
        errors += 1
    
    # Check environment
    print("Checking environment...")
    if check_file(".env"):
        print_success(".env file exists")
        
        # Check for API keys
        try:
            with open(".env", "r") as f:
                content = f.read()
                if "OPENAI_API_KEY=your-openai-api-key-here" in content or "OPENAI_API_KEY=" not in content:
                    print_warning("OPENAI_API_KEY not configured in .env")
                    warnings += 1
                else:
                    print_success("OPENAI_API_KEY configured")
        except Exception:
            pass
    else:
        print_warning(".env file not found (copy from env.example)")
        warnings += 1
    
    # Check Docker services
    print("Checking Docker services...")
    docker_compose_cmd = "docker-compose"
    if not run_command("docker-compose --version"):
        if run_command("docker compose version"):
            docker_compose_cmd = "docker compose"
        else:
            print_error("docker-compose not found")
            errors += 1
            docker_compose_cmd = None
    
    if docker_compose_cmd:
        print_success("docker-compose available")
        
        # Check if services are running
        result = subprocess.run(
            f"{docker_compose_cmd} ps",
            shell=True,
            capture_output=True,
            text=True
        )
        if "Up" in result.stdout:
            print_success("Docker services are running")
        else:
            print_warning("Docker services not running (run: docker-compose up -d)")
            warnings += 1
    
    # Check spaCy model
    print("Checking spaCy model...")
    if check_dir("backend/venv"):
        venv_python = Path("backend/venv/bin/python")
        if sys.platform == "win32":
            venv_python = Path("backend/venv/Scripts/python.exe")
        
        if venv_python.exists():
            result = subprocess.run(
                [str(venv_python), "-c", "import spacy; spacy.load('en_core_web_sm')"],
                capture_output=True
            )
            if result.returncode == 0:
                print_success("spaCy model installed")
            else:
                print_warning("spaCy model not found (run: python -m spacy download en_core_web_sm)")
                warnings += 1
    
    # Summary
    print_header("Verification Summary")
    
    if errors == 0 and warnings == 0:
        print_success("All checks passed! Installation looks good.")
        sys.exit(0)
    elif errors == 0:
        print_warning(f"Installation complete with {warnings} warning(s)")
        print_info("Review warnings above and fix if needed")
        sys.exit(0)
    else:
        print_error(f"Installation incomplete: {errors} error(s), {warnings} warning(s)")
        print_info("Please fix errors and run installation script again")
        sys.exit(1)

if __name__ == "__main__":
    main()


