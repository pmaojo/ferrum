import sys
import types
import pytest
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Stub heavy optional dependencies before importing server
for mod_name, cls_name in [
    ("adapters.inmemory_tracing_adapter", "InMemoryTracingAdapter"),
    ("adapters.llm.openai_audio_embedding_adapter", "OpenAIAudioEmbeddingAdapter"),
    ("adapters.llm.openai_image_embedding_adapter", "OpenAIImageEmbeddingAdapter"),
    ("adapters.retrievers.falkordb_graph_adapter", "FalkorGraphAdapter"),
]:
    module = types.ModuleType(mod_name)
    setattr(module, cls_name, type(cls_name, (), {}))
    sys.modules.setdefault(mod_name, module)

# Stub unused routers to avoid heavy dependencies
from fastapi import APIRouter
for name in [
    "cache",
    "agents",
    "docs_ingestion",
    "ecommerce_context",
    "feature_request",
    "gremlin",
    "health",
    # ingestion and query will use real modules
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
    mod = types.ModuleType(f"ui_adapters.rest_api.routes.{name}")
    mod.router = APIRouter()
    if name == "cache":
        mod.cache = {}
    sys.modules[f"ui_adapters.rest_api.routes.{name}"] = mod

from domain.auth import Role
from domain.entities import ValidationReport
from ui_adapters.rest_api.server import app, create_access_token
from ui_adapters.rest_api.dependencies import (
    ApplicationContainer,
    get_container,
    get_llm,
)


@pytest.fixture
def service_container():
    container = ApplicationContainer()
    container.config.from_dict({})
    container.ingestion_service.override(Mock())
    container.query_service.override(Mock())
    return container


@pytest.fixture
def client(service_container):
    with patch(
        "ui_adapters.rest_api.dependencies.create_default_container",
        return_value=service_container,
    ):
        app.dependency_overrides[get_container] = lambda: service_container
        app.dependency_overrides[get_llm] = lambda: Mock()
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


def make_token(role: Role) -> str:
    return create_access_token({"sub": "user", "role": role.value})


def test_query_authorized(client, service_container):
    svc = service_container.query_service()
    svc.execute_natural_language_query.return_value = {"ok": True}
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {make_token(Role.QUERY)}"},
        json={"question": "q", "kg_id": "kg", "tenant_id": "t", "user_id": "u"},
    )
    assert resp.status_code == 200
    svc.execute_natural_language_query.assert_called_once()


def test_query_forbidden_role(client, service_container):
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {make_token(Role.INGEST)}"},
        json={"question": "q", "kg_id": "kg", "tenant_id": "t", "user_id": "u"},
    )
    assert resp.status_code == 403


def test_ingest_authorized(client, service_container):
    report = ValidationReport(
        tenant_id="t",
        is_consistent=True,
        violated_rules=[],
        unsat_classes=[],
        repair_suggestions=[],
        explanation=None,
        ontology_version_id="v1",
    )
    svc = service_container.ingestion_service()
    svc.process_documents.return_value = report
    resp = client.post(
        "/api/ingest",
        headers={"Authorization": f"Bearer {make_token(Role.INGEST)}"},
        json={
            "documents": [{"content": "doc"}],
            "kg_id": "kg",
            "tenant_id": "t",
            "ontology_version_id": "v1",
        },
    )
    assert resp.status_code == 200
    svc.process_documents.assert_called_once()


def test_ingest_unauthorized_no_token(client):
    resp = client.post(
        "/api/ingest",
        json={
            "documents": [{"content": "doc"}],
            "kg_id": "kg",
            "tenant_id": "t",
            "ontology_version_id": "v1",
        },
    )
    assert resp.status_code == 401
