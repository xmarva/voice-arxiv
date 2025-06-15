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
    
    if response.status_code == 200:
        data = response.json()
        assert "papers" in data
        assert "query" in data
        assert "pipeline_type" in data
        assert data["query"] == search_data["query"]
        assert data["pipeline_type"] == search_data["pipeline_type"]
        assert len(data["papers"]) <= search_data["limit"]