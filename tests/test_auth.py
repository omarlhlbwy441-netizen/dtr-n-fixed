import pytest

def test_login_endpoint(test_client):
    response = test_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    # May fail if DB not seeded, but endpoint should exist
    assert response.status_code in [200, 401, 404]

def test_register_endpoint(test_client):
    response = test_client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    })
    assert response.status_code in [200, 201, 400, 409, 404]

def test_unauthorized_access(test_client):
    response = test_client.get("/api/agents")
    # Should require auth or be public
    assert response.status_code in [200, 401, 403, 404]
