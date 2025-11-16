import sys
from pathlib import Path
from types import SimpleNamespace, ModuleType

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

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
# Create minimal query router
query_mod = ModuleType("ui_adapters.rest_api.routes.query")
query_router = APIRouter()

from ui_adapters.rest_api.models import QueryRequest

@query_router.post("/api/v1/query")
async def query_endpoint(request: QueryRequest):
    return {"received": request.question}

query_mod.router = query_router

# Add empty routers for other modules referenced in server
for name in [
    "cache",
    "agents",
    "docs_ingestion",
    "ecommerce_context",
    "feature_request",
    "gremlin",
    "health",
    "ingestion",
    "repo_ingestion",
    "llm",
    "llm_status",
    "multimodal",
    "ontology_versions",
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

routes_pkg.query = query_mod
sys.modules["ui_adapters.rest_api.routes"] = routes_pkg

from ui_adapters.rest_api import server
from ui_adapters.rest_api.server import app, get_current_user
from domain.auth import User, Role

app.dependency_overrides[get_current_user] = lambda: User(username="tester", role=Role.QUERY)

client = TestClient(app)


def test_invalid_kg_id_rejected():
    response = client.post(
        "/api/v1/query",
        json={"question": "hello", "kg_id": "bad id", "tenant_id": "tenant"},
    )
    assert response.status_code == 422


def test_payload_too_large_rejected(monkeypatch):
    monkeypatch.setattr(server, "MAX_PAYLOAD_SIZE", 100)
    big_question = "x" * 200
    response = client.post(
        "/api/v1/query",
        json={"question": big_question, "kg_id": "kg1", "tenant_id": "tenant"},
    )
    assert response.status_code == 413
