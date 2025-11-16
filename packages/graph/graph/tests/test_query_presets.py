from pathlib import Path
import sys
import types
import importlib.util
from unittest.mock import MagicMock

import pytest
pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def test_app():
    mock_query_service = MagicMock()
    container = types.SimpleNamespace(query_service=mock_query_service)

    # Stub dependencies
    dependencies_stub = types.SimpleNamespace(
        ServiceContainer=types.SimpleNamespace,
        get_container=lambda: container,
        create_default_container=lambda *_, **__: container,
    )
    sys.modules["ui_adapters.rest_api.dependencies"] = dependencies_stub

    # Load models module without importing package
    base = Path(__file__).resolve().parents[1] / "ui_adapters" / "rest_api"
    models_spec = importlib.util.spec_from_file_location(
        "ui_adapters.rest_api.models", base / "models.py"
    )
    models_module = importlib.util.module_from_spec(models_spec)
    models_spec.loader.exec_module(models_module)
    sys.modules["ui_adapters.rest_api.models"] = models_module

    # Stub cache module
    sys.modules["ui_adapters.rest_api.routes.cache"] = types.SimpleNamespace(cache={})

    # Load query module
    query_spec = importlib.util.spec_from_file_location(
        "query_module", base / "routes" / "query.py"
    )
    query_module = importlib.util.module_from_spec(query_spec)
    query_spec.loader.exec_module(query_module)

    app = FastAPI()
    app.include_router(query_module.router)
    return app, mock_query_service


@pytest.fixture
def client(test_app):
    app, _ = test_app
    with TestClient(app) as client:
        yield client


def test_list_queries_returns_presets(client):
    response = client.get("/api/v1/queries")
    assert response.status_code == 200
    data = response.json()
    ids = {q["id"] for q in data["queries"]}
    assert "sample" in ids


def test_execute_query_runs_sparql(client, test_app):
    app, mock_query_service = test_app
    mock_query_service.execute_sparql.return_value = {"rows": [{"s": "a"}], "graph": []}
    response = client.post(
        "/api/v1/queries/sample/execute", json={"tenant_id": "test-tenant"}
    )
    assert response.status_code == 200
    assert response.json() == {"rows": [{"s": "a"}], "graph": []}
    query_text = (Path(__file__).resolve().parents[1] / "application" / "queries" / "sample.rq").read_text()
    mock_query_service.execute_sparql.assert_called_once_with(
        tenant_id="test-tenant", query=query_text
    )
