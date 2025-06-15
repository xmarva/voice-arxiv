#!/usr/bin/env python
"""
Load arXiv papers into Weaviate database.
This script can be run separately from the main application.
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Add the project root to the Python path
root_dir = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, root_dir)

from src.config.logging_config import setup_logging
from src.database.data_loader import load_data
from src.config.settings import settings

def main():
    parser = argparse.ArgumentParser(description="Load arXiv papers into Weaviate")
    parser.add_argument(
        "--count", 
        type=int, 
        default=100,
        help="Number of papers to load (default: 100)"
    )
    parser.add_argument(
        "--categories", 
        type=str, 
        default=None,
        help=f"arXiv categories (comma separated, default: {settings.arxiv_categories})"
    )
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Update settings if categories are provided
    if args.categories:
        settings.arxiv_categories = args.categories
    
    logger.info(f"Starting data loading process for {args.count} arXiv papers")
    logger.info(f"Categories: {settings.arxiv_categories}")
    
    try:
        # Load the data
        load_data(max_results=args.count)
        logger.info("Data loading completed successfully")
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 