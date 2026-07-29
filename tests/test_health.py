import pytest

def test_health_endpoint(test_client):
    response = test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "rafeeq-kernel"
    assert data["version"] == "2.3.0"

def test_db_health(test_client):
    response = test_client.get("/api/health/db")
    assert response.status_code in [200, 503]  # 503 if DB not connected

def test_redis_health(test_client):
    response = test_client.get("/api/health/redis")
    assert response.status_code in [200, 503]

def test_github_health(test_client):
    response = test_client.get("/api/health/github")
    assert response.status_code in [200, 503]

def test_metrics_endpoint(test_client):
    response = test_client.get("/api/health/metrics")
    assert response.status_code == 200
    assert "rafeeq_requests_total" in response.text or response.text.startswith("#")

def test_readiness_probe(test_client):
    response = test_client.get("/api/health/ready")
    assert response.status_code in [200, 503]

def test_liveness_probe(test_client):
    response = test_client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
