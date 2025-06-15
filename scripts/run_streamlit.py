#!/usr/bin/env python
"""
Run the Streamlit frontend for the Research AI Assistant.
This assumes the FastAPI backend is already running.
"""

import sys
import os
import subprocess
import logging
from pathlib import Path

# Add the project root to the Python path
root_dir = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, root_dir)

from src.config.logging_config import setup_logging

def main():
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Path to streamlit app
    streamlit_app = os.path.join(root_dir, "frontend", "streamlit_app.py")
    
    if not os.path.exists(streamlit_app):
        logger.error(f"Streamlit app not found at {streamlit_app}")
        sys.exit(1)
    
    logger.info(f"Starting Streamlit frontend from {streamlit_app}")
    
    try:
        # Run streamlit
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", streamlit_app, "--server.port", "8501"],
            check=True
        )
    except KeyboardInterrupt:
        logger.info("Streamlit frontend stopped by user")
    except subprocess.CalledProcessError as e:
        logger.error(f"Streamlit frontend exited with error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running Streamlit frontend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 