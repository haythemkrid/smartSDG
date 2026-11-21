"""Tests for the FastAPI application."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_mock_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Add mock_module to modules directory for testing."""
    import sys
    from pathlib import Path

    # Add tests/fixtures to Python path so mock_module can be imported
    fixtures_path = Path(__file__).parent / "fixtures"
    if str(fixtures_path) not in sys.path:
        sys.path.insert(0, str(fixtures_path))


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_modules(client: TestClient) -> None:
    """Test GET /modules returns deployed modules."""
    response = client.get("/modules")
    assert response.status_code == 200

    modules = response.json()
    assert isinstance(modules, list)

    # Should have hydrowatch and urbanpulse (deployed by default)
    module_ids = [m["id"] for m in modules]
    assert "hydrowatch" in module_ids
    assert "urbanpulse" in module_ids
    # soilguard should NOT be in the list (not deployed)
    assert "soilguard" not in module_ids


def test_list_modules_structure(client: TestClient) -> None:
    """Test that module list has correct structure."""
    response = client.get("/modules")
    assert response.status_code == 200

    modules = response.json()
    for module in modules:
        assert "id" in module
        assert "version" in module
        assert "title" in module
        assert "sdg" in module
        assert "sensors" in module
        assert "indices" in module
        assert "aoi_id" in module
        assert "outputs" in module
        assert isinstance(module["outputs"], list)
        for output in module["outputs"]:
            assert "name" in output
            assert "type" in output


def test_undeployed_module_not_listed(client: TestClient) -> None:
    """Test that undeployed modules don't appear in /modules."""
    response = client.get("/modules")
    assert response.status_code == 200

    modules = response.json()
    module_ids = [m["id"] for m in modules]
    assert "soilguard" not in module_ids


def test_get_layers_for_deployed_module(client: TestClient) -> None:
    """Test GET /modules/{id}/layers for deployed module."""
    response = client.get("/modules/hydrowatch/layers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_layers_for_undeployed_module(client: TestClient) -> None:
    """Test GET /modules/{id}/layers returns 404 for undeployed module."""
    response = client.get("/modules/soilguard/layers")
    assert response.status_code == 404


def test_get_timeseries_for_deployed_module(client: TestClient) -> None:
    """Test GET /modules/{id}/timeseries for deployed module."""
    response = client.get("/modules/hydrowatch/timeseries")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_timeseries_for_undeployed_module(client: TestClient) -> None:
    """Test GET /modules/{id}/timeseries returns 404 for undeployed module."""
    response = client.get("/modules/soilguard/timeseries")
    assert response.status_code == 404


def test_get_runs_for_deployed_module(client: TestClient) -> None:
    """Test GET /modules/{id}/runs for deployed module."""
    response = client.get("/modules/hydrowatch/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_runs_for_undeployed_module(client: TestClient) -> None:
    """Test GET /modules/{id}/runs returns 404 for undeployed module."""
    response = client.get("/modules/soilguard/runs")
    assert response.status_code == 404


def test_get_layer_not_found(client: TestClient) -> None:
    """Test GET /modules/{id}/layers/{name} returns 404."""
    response = client.get("/modules/hydrowatch/layers/nonexistent")
    assert response.status_code == 404


def test_openapi_docs(client: TestClient) -> None:
    """Test that OpenAPI docs are available at /docs."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_json(client: TestClient) -> None:
    """Test that OpenAPI JSON schema is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
