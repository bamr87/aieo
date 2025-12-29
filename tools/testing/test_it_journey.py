#!/usr/bin/env python3
"""
AIEO Test on IT-Journey Repository
Direct API test without requiring backend to be pre-started
"""

import os
import sys
import subprocess
import time
import requests
import json
from pathlib import Path

def main():
    print("=" * 60)
    print("  AIEO Test on IT-Journey Repository")
    print("=" * 60)
    print()
    
    # Change to project root
    os.chdir(Path(__file__).parent.parent.parent)
    
    # Check if backend is running
    print("Checking backend status...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✓ Backend is running")
            backend_running = True
        else:
            backend_running = False
    except:
        backend_running = False
    
    if not backend_running:
        print("✗ Backend not running")
        print("\nStarting backend...")
        
        backend_dir = Path("backend")
        venv_python = backend_dir / "venv" / "bin" / "python"
        
        if not venv_python.exists():
            print("ERROR: Backend venv not found")
            print("Please run: ./scripts/install.sh")
            return
        
        # Start backend
        process = subprocess.Popen(
            [str(venv_python), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for backend
        for i in range(15):
            time.sleep(1)
            try:
                response = requests.get("http://localhost:8000/health", timeout=1)
                if response.status_code == 200:
                    print("✓ Backend started successfully")
                    backend_running = True
                    break
            except:
                pass
        
        if not backend_running:
            print("✗ Backend failed to start")
            stderr = process.stderr.read().decode() if process.stderr else ""
            print(f"Error: {stderr[:500]}")
            return
    
    # Test 1: README
    print("\n" + "=" * 60)
    print("  Test 1: Auditing IT-Journey README.md")
    print("=" * 60)
    print()
    
    readme_path = Path("/Users/bamr87/github/it-journey/README.md")
    if not readme_path.exists():
        print(f"✗ README not found: {readme_path}")
    else:
        print(f"✓ Found README: {readme_path}")
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        print(f"Content length: {len(content)} characters")
        print("Sending audit request...")
        
        try:
            # Limit content size for testing
            test_content = content[:10000]
            
            response = requests.post(
                "http://localhost:8000/api/v1/aieo/audit",
                json={
                    "content": test_content,
                    "format": "markdown"
                },
                headers={"X-API-Key": "test-key-1234567890"},
                timeout=30
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("\n" + "=" * 60)
                print("✓ AUDIT SUCCESSFUL!")
                print("=" * 60)
                print(f"\nScore: {result.get('score', 0)}/100")
                print(f"Grade: {result.get('grade', 'F')}")
                
                gaps = result.get('gaps', [])
                if gaps:
                    print(f"\nTop {min(5, len(gaps))} Gaps Found:")
                    print("-" * 60)
                    for i, gap in enumerate(gaps[:5], 1):
                        print(f"\n{i}. Category: {gap.get('category', 'unknown')}")
                        print(f"   Severity: {gap.get('severity', 'unknown')}")
                        print(f"   Description: {gap.get('description', '')}")
                else:
                    print("\nNo gaps found!")
            else:
                print(f"\n✗ Error: HTTP {response.status_code}")
                print(response.text[:500])
                
        except Exception as e:
            print(f"\n✗ Error: {e}")
    
    # Test 2: Website
    print("\n" + "=" * 60)
    print("  Test 2: Auditing IT-Journey Website")
    print("=" * 60)
    print()
    
    print("Testing: https://it-journey.dev")
    print("Sending audit request...")
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/aieo/audit",
            json={"url": "https://it-journey.dev"},
            headers={"X-API-Key": "test-key-1234567890"},
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n" + "=" * 60)
            print("✓ AUDIT SUCCESSFUL!")
            print("=" * 60)
            print(f"\nScore: {result.get('score', 0)}/100")
            print(f"Grade: {result.get('grade', 'F')}")
            
            gaps = result.get('gaps', [])
            if gaps:
                print(f"\nTop {min(5, len(gaps))} Gaps Found:")
                print("-" * 60)
                for i, gap in enumerate(gaps[:5], 1):
                    print(f"\n{i}. Category: {gap.get('category', 'unknown')}")
                    print(f"   Severity: {gap.get('severity', 'unknown')}")
                    print(f"   Description: {gap.get('description', '')}")
        else:
            print(f"\n✗ Error: HTTP {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("  Testing Complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

