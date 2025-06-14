#!/bin/bash

echo "Setting up Research AI Assistant..."

if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

echo "Creating necessary directories..."
mkdir -p logs
mkdir -p data
mkdir -p frontend/static/css
mkdir -p frontend/static/js
mkdir -p frontend/templates

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Setting up Docker environment..."
cd infrastructure/docker
docker-compose up -d weaviate prometheus grafana

echo "Waiting for services to start..."
sleep 30

echo "Checking service health..."
curl -f http://localhost:8080/v1/meta || echo "Weaviate not ready yet"
curl -f http://localhost:9090/-/healthy || echo "Prometheus not ready yet"
curl -f http://localhost:3000/api/health || echo "Grafana not ready yet"

echo "Setup complete!"
echo "Services:"
echo "- Weaviate: http://localhost:8080"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "To start the application:"
echo "python -m src.api.main"
echo ""
echo "Or with Docker:"
echo "docker-compose up app"