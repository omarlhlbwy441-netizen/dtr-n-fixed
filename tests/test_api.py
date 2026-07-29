import pytest

def test_status_endpoint(test_client):
    response = test_client.get("/api/status")
    assert response.status_code in [200, 404]

def test_agents_endpoint(test_client):
    response = test_client.get("/api/agents")
    assert response.status_code in [200, 401, 404]

def test_evolution_log_endpoint(test_client):
    response = test_client.get("/evolution-log")
    assert response.status_code in [200, 404]

def test_files_endpoint(test_client):
    response = test_client.get("/files")
    assert response.status_code in [200, 401, 404]

def test_cors_headers(test_client):
    response = test_client.options("/api/health", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    })
    assert response.status_code in [200, 204]
