#!/bin/bash

echo "Starting LLM service in CPU mode..."

# Go to the docker directory
cd infrastructure/docker

# Stop the existing LLM service if running
docker-compose stop llm-service

# Start the LLM service with CPU mode
DEVICE=cpu docker-compose up -d llm-service

echo "LLM service started in CPU mode. Check logs with:"
echo "docker-compose logs -f llm-service" 