import pytest
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "postgresql://postgres:test@localhost:5432/rafeeq_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["RATE_LIMIT_ENABLED"] = "false"

@pytest.fixture(scope="session")
def test_client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)

@pytest.fixture
def auth_headers(test_client):
    # Login to get token
    response = test_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    return {}
