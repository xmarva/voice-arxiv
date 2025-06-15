#!/bin/bash

# Скрипт для исправления ошибок и пересборки системы
echo "Stopping existing containers..."
cd "$(dirname "$0")/../infrastructure/docker"
docker-compose down

echo "Cleaning up volumes for fresh start..."
docker volume rm docker_weaviate_data || true

echo "Building containers..."
docker-compose build --no-cache

echo "Starting Weaviate..."
docker-compose up -d weaviate
echo "Waiting for Weaviate to initialize (30 seconds)..."
sleep 30

echo "Starting API, Streamlit, Prometheus and Grafana..."
docker-compose up -d api streamlit prometheus grafana

echo "Waiting for API to start (10 seconds)..."
sleep 10

echo "Loading sample data..."
docker-compose run --rm scraper python scripts/load_arxiv_data.py --count 100

echo "System should now be running correctly!"
echo "- API: http://localhost:8000"
echo "- Streamlit UI: http://localhost:8501"
echo "- Weaviate Console: http://localhost:8080/v1/console"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000"

# Check if the services are running
echo -e "\nChecking service status:"
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API is running"
else
    echo "❌ API is not running"
fi

if curl -s http://localhost:8080/v1/.well-known/ready > /dev/null; then
    echo "✅ Weaviate is running"
else
    echo "❌ Weaviate is not running"
fi

if curl -s http://localhost:8501 > /dev/null; then
    echo "✅ Streamlit is running"
else
    echo "❌ Streamlit is not running"
fi

if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "✅ Prometheus is running"
else
    echo "❌ Prometheus is not running"
fi

if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✅ Grafana is running"
else
    echo "❌ Grafana is not running"
fi

echo -e "\nTo rebuild the system if you encounter issues:"
echo "1. Run this script again: bash scripts/fix-and-rebuild.sh"
echo "2. Or manually restart individual services: docker-compose restart api streamlit" 