import os
from unittest.mock import MagicMock

import pytest
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from fastapi import FastAPI

from ui_adapters.rest_api.routes.gremlin import router
from ui_adapters.rest_api.dependencies import ApplicationContainer, get_container


@pytest.fixture
def test_client(mock_container):
    app = FastAPI()
    app.dependency_overrides[get_container] = lambda: mock_container
    app.include_router(router)
    from domain.exceptions import GraphRAGException
    from fastapi.responses import JSONResponse

    @app.exception_handler(GraphRAGException)
    async def handler(_, exc: GraphRAGException):
        return JSONResponse(
            status_code=400,
            content={"error": exc.error_code, "message": exc.message},
        )
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_container():
    graph_traversal = MagicMock()
    graph_traversal.execute_traversal.return_value = [{"x": 1}]
    container = ApplicationContainer()
    container.config.from_dict({})
    container.ingestion_service.override(MagicMock())
    container.query_service.override(MagicMock())
    container.workflow_orchestrator.override(MagicMock())
    container.token_budget_service.override(MagicMock())
    container.observability_service.override(MagicMock())
    container.context_compression_service.override(MagicMock())
    container.llm_fallback_policy.override(MagicMock())
    container.job_repository.override(MagicMock())
    container.ontology_version_service.override(MagicMock())
    container.graph_traversal.override(graph_traversal)
    return container


def test_execute_gremlin_query(test_client, mock_container):
    response = test_client.post(
        "/api/gremlin",
        json={"query": "g.V().limit(1)"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    assert response.json() == {"records": [{"x": 1}]}
    mock_container.graph_traversal.execute_traversal.assert_called_once_with(
        "g.V().limit(1)"
    )


def test_execute_gremlin_query_validation_error(test_client):
    response = test_client.post(
        "/api/gremlin",
        json={"query": ""},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "APPLICATION_VALIDATION_ERROR"

