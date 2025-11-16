import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

sys.path.append(str(Path(__file__).resolve().parents[2]))

# Stub heavy dependency module before importing server
stub_deps = ModuleType("ui_adapters.rest_api.dependencies")


def create_default_container(*args, **kwargs):
    return SimpleNamespace()


def get_container(*args, **kwargs):
    return SimpleNamespace(
        query_service=SimpleNamespace(execute_natural_language_query=lambda **kw: {})
    )


stub_deps.create_default_container = create_default_container
stub_deps.get_container = get_container
stub_deps.resolve = lambda container, name: None
stub_deps.ServiceContainer = object
sys.modules["ui_adapters.rest_api.dependencies"] = stub_deps

# Stub routes package
routes_pkg = ModuleType("ui_adapters.rest_api.routes")
# Create minimal health router
health_mod = ModuleType("ui_adapters.rest_api.routes.health")
health_router = APIRouter()


@health_router.get("/api/health")
async def health_endpoint():
    return {"status": "ok"}


health_mod.router = health_router

# Add empty routers for modules referenced in server
for name in [
    "cache",
    "agents",
    "docs_ingestion",
    "ecommerce_context",
    "feature_request",
    "gremlin",
    "ingestion",
    "repo_ingestion",
    "llm",
    "llm_status",
    "multimodal",
    "ontology_versions",
    "query",
    "repository",
    "structrag",
    "sync",
    "token_budget",
    "training",
    "visualization",
    "workflows",
]:
    mod = ModuleType(f"ui_adapters.rest_api.routes.{name}")
    mod.router = APIRouter()
    setattr(routes_pkg, name, mod)

routes_pkg.health = health_mod
sys.modules["ui_adapters.rest_api.routes"] = routes_pkg


def _get_client():
    import ui_adapters.rest_api.server as server
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)
    importlib.reload(server)
    return TestClient(server.app)


def test_blocked_origin(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://allowed.com"]')
    client = _get_client()
    response = client.get("/", headers={"Origin": "https://evil.com"})
    assert "access-control-allow-origin" not in response.headers
