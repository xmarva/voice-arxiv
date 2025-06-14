# Research AI Assistant

Research paper analysis and discovery system using LangChain, Weaviate, and custom LLM models. This is a project with a focus on infrastructure design, monitoring and metrics.

## Quick Start

### 1. Environment Setup

```bash
# Clone and setup
git clone git@github.com:xmarva/voice-arxiv.git
cd voice-arxiv

# Copy environment variables
cp .env.example .env
# Edit .env with your HuggingFace API key

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2. Start Services

```bash
# Option 1: Docker Compose
cd infrastructure/docker
docker-compose up -d

# Option 2: Local Development
python -m src.api.main
```

### 3. Access Services Locally

- **Application**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Weaviate**: http://localhost:8080

## Configuration

### Environment Variables

```bash
# Core Services
WEAVIATE_URL=http://localhost:8080
HUGGINGFACE_API_KEY=your_token

# Models
LLM_MODEL_NAME=microsoft/DialoGPT-medium
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

## Development

### Project Structure

```
research-ai-assistant/
├── src/                 # Core application code
│   ├── api/            # FastAPI routes and main app
│   ├── database/       # Weaviate client and data management
│   ├── rag/            # RAG pipeline implementations
│   ├── agents/         # LangChain agents and tools
│   ├── models/         # LLM and embedding models
│   ├── monitoring/     # Metrics and profiling
│   └── utils/          # Utilities (arXiv scraper, etc.)
├── infrastructure/     # Docker, K8s, monitoring configs
├── frontend/          # Static web UI
├── tests/             # Test suite
└── scripts/           # Setup and deployment scripts
```

### Running Tests

```bash
pytest tests/ -v
```

## Monitoring

### Metrics Available

- Request latency and throughput
- RAG pipeline performance
- LLM generation time
- Weaviate search duration
- System resource usage

### Grafana Dashboards

Pre-configured dashboards track:
- API performance metrics
- RAG pipeline latency
- Database query performance
- System health indicators

## Deployment

### Docker Production

```bash
cd infrastructure/docker
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
kubectl apply -f infrastructure/deployment/k8s/
```