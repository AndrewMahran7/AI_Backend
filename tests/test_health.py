"""Tests for health, system info, and root endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    """GET / should return service identity."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["status"] == "running"
    assert "environment" in data


def test_health_endpoint() -> None:
    """GET /api/v1/health should return status ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_system_info_endpoint() -> None:
    """GET /api/v1/system/info should return non-secret runtime info."""
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "app_name" in data
    assert "version" in data
    assert "environment" in data
    assert "debug" in data
    assert "api_prefix" in data
    assert "database_configured" in data
    assert "gemini_configured" in data
