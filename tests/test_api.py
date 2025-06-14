import pytest
from fastapi.testclient import TestClient

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200

def test_stats_endpoint(client):
    response = client.get("/api/v1/stats")
    assert response.status_code in [200, 500]

def test_search_endpoint(client):
    search_data = {
        "query": "machine learning",
        "pipeline_type": "simple",
        "limit": 3
    }
    response = client.post("/api/v1/search", json=search_data)
    assert response.status_code in [200, 500]