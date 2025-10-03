#!/usr/bin/env python3
"""
Simple startup script for ISRO HelpBot
"""
import subprocess
import sys
import os

def main():
    print("🚀 Starting ISRO HelpBot...")
    print("📡 Backend: http://localhost:8001")
    print("🌐 Frontend: http://localhost:3000")
    print("📚 API Docs: http://localhost:8001/docs")
    print("\nPress Ctrl+C to stop")
    
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_dir)
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "127.0.0.1", 
            "--port", "8001", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == "__main__":
    main()
