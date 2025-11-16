import types
import sys
from unittest.mock import Mock

import pytest
pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create stub dependencies module before importing health router
container_instance = None

def _create_stub_module():
    global container_instance
    deps = types.ModuleType("ui_adapters.rest_api.dependencies")

    class ServiceContainer:  # minimal container placeholder
        pass

    container_instance = ServiceContainer()

    def get_container():
        return container_instance

    deps.ServiceContainer = ServiceContainer
    deps.get_container = get_container
    sys.modules["ui_adapters.rest_api.dependencies"] = deps

_create_stub_module()

from ui_adapters.rest_api.routes import health


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(health.router)

    # configure default healthy services
    container_instance.falkor_adapter = Mock()
    container_instance.falkor_adapter.client = Mock()
    container_instance.falkor_adapter.client.ping.return_value = True

    container_instance.message_bus = Mock()
    container_instance.message_bus.publish.return_value = None

    container_instance.cache_port = Mock()
    container_instance.cache_port._client = Mock()
    container_instance.cache_port._client.ping.return_value = True

    with TestClient(app) as test_client:
        yield test_client


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["components"] == {
        "database": "ok",
        "message_bus": "ok",
        "cache": "ok",
    }


def test_health_database_failure(client):
    container_instance.falkor_adapter.client.ping.side_effect = Exception("down")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["components"]["database"] == "error"


def test_health_message_bus_failure(client):
    container_instance.message_bus.publish.side_effect = Exception("down")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["components"]["message_bus"] == "error"


def test_health_cache_failure(client):
    container_instance.cache_port._client.ping.side_effect = Exception("down")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["components"]["cache"] == "error"
