#!/bin/bash

# Script to rebuild and restart all components of the Research AI Assistant

echo "Stopping existing containers..."
cd "$(dirname "$0")/../infrastructure/docker"
docker-compose down

echo "Building containers..."
docker-compose build --no-cache

echo "Starting all services..."
docker-compose up -d

echo "Waiting for services to start..."
sleep 5

# Check if Weaviate is ready
echo "Checking Weaviate status..."
MAX_ATTEMPTS=30
ATTEMPT=0
READY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ] && [ "$READY" = false ]; do
  if curl -s -f http://localhost:8080/v1/.well-known/ready > /dev/null; then
    READY=true
    echo "Weaviate is ready!"
  else
    ATTEMPT=$((ATTEMPT+1))
    echo "Waiting for Weaviate... Attempt $ATTEMPT/$MAX_ATTEMPTS"
    sleep 2
  fi
done

if [ "$READY" = false ]; then
  echo "Weaviate failed to start. Check logs for details."
  echo "You can check logs with: docker-compose logs weaviate"
  exit 1
fi

# Check API status
echo "Checking API status..."
ATTEMPT=0
API_READY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ] && [ "$API_READY" = false ]; do
  if curl -s -f http://localhost:8000/health > /dev/null; then
    API_READY=true
    echo "API is ready!"
  else
    ATTEMPT=$((ATTEMPT+1))
    echo "Waiting for API... Attempt $ATTEMPT/$MAX_ATTEMPTS"
    sleep 2
  fi
done

if [ "$API_READY" = false ]; then
  echo "API failed to start. Check logs for details."
  echo "You can check logs with: docker-compose logs api"
  exit 1
fi

# Check paper count
echo "Checking paper count..."
PAPER_COUNT=$(curl -s -f "http://localhost:8000/api/v1/stats" | grep -o '"paper_count":[0-9]*' | cut -d':' -f2)

if [ "$PAPER_COUNT" = "0" ] || [ -z "$PAPER_COUNT" ]; then
  echo "No papers found in database. Running scraper..."
  docker-compose run --rm scraper python scripts/load_arxiv_data.py --count 100
else
  echo "Found $PAPER_COUNT papers in database."
fi

echo "System is ready!"
echo "- API: http://localhost:8000"
echo "- Streamlit: http://localhost:8501"
echo "- Weaviate Console: http://localhost:8080/v1/console"

exit 0 