#!/bin/bash

# This script runs the arXiv scraper in Docker

# Navigate to the docker directory
cd "$(dirname "$0")/../infrastructure/docker"

# Run the scraper service
docker-compose run --rm scraper python scripts/load_arxiv_data.py "$@"

echo "Scraper completed. Check the data directory for results." 