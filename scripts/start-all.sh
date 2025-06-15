#!/bin/bash

# Script to start all components of the Research AI Assistant

# Navigate to the docker directory
cd "$(dirname "$0")/../infrastructure/docker"

# Function to check if Weaviate is ready
check_weaviate() {
  echo "Checking if Weaviate is ready..."
  local max_attempts=30
  local attempt=0
  
  while [ $attempt -lt $max_attempts ]; do
    if curl -s -f http://localhost:8080/v1/.well-known/ready > /dev/null; then
      echo "Weaviate is ready!"
      return 0
    fi
    
    attempt=$((attempt+1))
    echo "Waiting for Weaviate to be ready... Attempt $attempt/$max_attempts"
    sleep 2
  done
  
  echo "Timed out waiting for Weaviate to be ready"
  return 1
}

# Start all services except scraper
echo "Starting core services..."
docker-compose up -d weaviate api streamlit prometheus grafana

# Wait for Weaviate to be ready
if check_weaviate; then
  # Check if we need to load data
  paper_count=$(curl -s -f "http://localhost:8000/api/v1/stats" | grep -o '"paper_count":[0-9]*' | cut -d':' -f2)
  
  if [ "$paper_count" = "0" ] || [ -z "$paper_count" ]; then
    echo "No papers found in Weaviate. Running scraper..."
    docker-compose run --rm scraper python scripts/load_arxiv_data.py --count 100
    echo "Scraper completed. Data should now be loaded."
  else
    echo "Found $paper_count papers in Weaviate. Skipping data loading."
  fi
else
  echo "Weaviate is not ready. Skipping data loading."
fi

echo "All services are up and running."
echo "- API & Web UI: http://localhost:8000"
echo "- Streamlit UI: http://localhost:8501"
echo "- Weaviate: http://localhost:8080"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000" 