"""
Compile and setup backend components for ISRO HelpBot
Ensures all dependencies are properly installed and configured
"""

import subprocess
import sys
import os
import asyncio
import logging
from pathlib import Path
import importlib.util
import py_compile
import glob

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is compatible"""
    logger.info(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        return False
    return True

def compile_python_files():
    """Compile all Python files to check for syntax errors"""
    logger.info("Compiling Python files...")
    files = glob.glob('*.py')
    err = False
    
    for f in files:
        try:
            py_compile.compile(f, doraise=True)
            logger.info(f'✅ Compiled: {f}')
        except Exception as e:
            logger.error(f'❌ Error compiling {f}: {e}')
            err = True
    
    if err:
        logger.error("Some files failed to compile")
        return False
    else:
        logger.info('All files compiled successfully')
        return True

def install_requirements():
    """Install Python requirements"""
    logger.info("Installing Python requirements...")
    try:
        # Upgrade pip first
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Install requirements
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logger.info("Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing requirements: {e}")
        return False

def download_nltk_data():
    """Download required NLTK data"""
    logger.info("Downloading NLTK data...")
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)
        logger.info("NLTK data downloaded successfully")
        return True
    except Exception as e:
        logger.warning(f"NLTK data download failed: {e}")
        logger.info("System will continue without NLTK features")
        return False

def download_spacy_model():
    """Download spaCy English model"""
    logger.info("Downloading spaCy English model...")
    try:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        logger.info("spaCy model downloaded successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"spaCy model download failed: {e}")
        logger.info("System will continue without spaCy features")
        return False

def setup_directories():
    """Create necessary directories"""
    directories = [
        "static",
        "static/uploads",
        "logs",
        "data",
        "data/cache",
        "data/exports",
        "__pycache__"
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")

def create_config_file():
    """Create configuration file if it doesn't exist"""
    config_content = """
# ISRO HelpBot Configuration

# MongoDB Configuration
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DBNAME=isro_chatbot

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# Scraping Configuration
SCRAPE_RATE_LIMIT=1.0
SCRAPE_MAX_PAGES=100
SCRAPE_MAX_DEPTH=2

# NLP Configuration
USE_NLTK=1
USE_SPACY=1
MAX_RESPONSE_LENGTH=500

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
"""
    
    config_path = Path(".env")
    if not config_path.exists():
        with open(config_path, "w") as f:
            f.write(config_content.strip())
        logger.info("Created .env configuration file")

async def test_database_connection():
    """Test MongoDB connection"""
    logger.info("Testing database connection...")
    try:
        import database
        db = await database.connect_to_mongodb()
        if db is not None:
            logger.info("Database connection successful")
            return True
        else:
            logger.warning("Database connection failed - continuing without persistence")
            return False
    except Exception as e:
        logger.warning(f"Database test failed: {e}")
        return False

async def initialize_content_manager():
    """Initialize content manager"""
    logger.info("Initializing content manager...")
    try:
        from content_manager import initialize_content_manager
        await initialize_content_manager()
        logger.info("Content manager initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Content manager initialization failed: {e}")
        return False

def validate_components():
    """Validate all backend components"""
    logger.info("Validating backend components...")
    
    required_files = [
        "main.py",
        "database.py",
        "nlp_engine.py",
        "routes.py",
        "search_utils.py",
        "scraper.py",
        "content_manager.py",
        "admin_routes.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        return False
    
    logger.info("All required files present")
    
    # Test imports
    logger.info("Testing module imports...")
    test_modules = [
        "fastapi",
        "uvicorn",
        "beautifulsoup4",
        "requests",
        "motor",
        "pymongo",
        "numpy",
        "scikit-learn"
    ]
    
    failed_imports = []
    for module in test_modules:
        try:
            importlib.import_module(module.replace('-', '_'))
        except ImportError:
            failed_imports.append(module)
    
    if failed_imports:
        logger.warning(f"Failed to import modules: {failed_imports}")
        logger.info("Run 'pip install -r requirements.txt' to install missing modules")
    else:
        logger.info("All required modules imported successfully")
    
    return True

def create_startup_script():
    """Create startup script for easy server launch"""
    startup_content = """#!/bin/bash
# ISRO HelpBot Startup Script

echo "Starting ISRO HelpBot backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
    
    startup_path = Path("start_server.sh")
    with open(startup_path, "w") as f:
        f.write(startup_content)
    
    # Make it executable on Unix systems
    try:
        os.chmod(startup_path, 0o755)
    except:
        pass
    
    logger.info("Created startup script: start_server.sh")

def create_windows_startup_script():
    """Create Windows startup script"""
    startup_content = """@echo off
REM ISRO HelpBot Windows Startup Script

echo Starting ISRO HelpBot backend...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Install requirements
pip install -r requirements.txt

REM Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
"""
    
    startup_path = Path("start_server.bat")
    with open(startup_path, "w") as f:
        f.write(startup_content)
    
    logger.info("Created Windows startup script: start_server.bat")

def print_completion_summary():
    """Print completion summary and next steps"""
    summary = """
    ╔══════════════════════════════════════════════════════════╗
    ║              ISRO HelpBot Backend Setup Complete         ║
    ╠══════════════════════════════════════════════════════════╣
    ║                                                          ║
    ║  🚀 Your ISRO HelpBot backend is ready to launch!       ║
    ║                                                          ║
    ║  Next Steps:                                             ║
    ║  1. Start the server:                                    ║
    ║     • Windows: run start_server.bat                     ║
    ║     • Linux/Mac: bash start_server.sh                   ║
    ║     • Manual: uvicorn main:app --reload                 ║
    ║                                                          ║
    ║  2. Access the API:                                      ║
    ║     • API Docs: http://localhost:8000/docs               ║
    ║     • Health Check: http://localhost:8000/health         ║
    ║     • Admin Dashboard: http://localhost:8000/admin       ║
    ║                                                          ║
    ║  3. Features Available:                                  ║
    ║     ✅ MOSDAC Web Scraper                                ║
    ║     ✅ Content Storage & Indexing                        ║
    ║     ✅ Real-time Chat System                             ║
    ║     ✅ NLP Query Processing                              ║
    ║     ✅ Admin Dashboard                                   ║
    ║     ✅ Analytics & Monitoring                            ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(summary)

async def main():
    """Main compilation and setup process"""
    logger.info("🚀 Starting ISRO HelpBot backend compilation...")
    
    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Compile Python files
    if not compile_python_files():
        logger.error("Python file compilation failed")
        sys.exit(1)
    
    # Step 3: Validate components
    if not validate_components():
        logger.error("Component validation failed")
        sys.exit(1)
    
    # Step 4: Setup directories
    setup_directories()
    
    # Step 5: Create configuration
    create_config_file()
    
    # Step 6: Install requirements
    if not install_requirements():
        logger.error("Requirements installation failed")
        sys.exit(1)
    
    # Step 7: Download NLTK data
    download_nltk_data()
    
    # Step 8: Download spaCy model
    download_spacy_model()
    
    # Step 9: Test database connection
    await test_database_connection()
    
    # Step 10: Initialize content manager
    await initialize_content_manager()
    
    # Step 11: Create startup scripts
    create_startup_script()
    create_windows_startup_script()
    
    # Step 12: Print completion summary
    print_completion_summary()
    
    logger.info("✅ Backend compilation and setup completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
