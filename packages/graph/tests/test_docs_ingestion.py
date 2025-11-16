import pytest
from unittest.mock import Mock, patch

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from ui_adapters.rest_api.server import app
from ui_adapters.rest_api.dependencies import (
    ApplicationContainer,
    get_container,
    get_llm,
)
from domain.entities import ValidationReport
from ui_adapters.rest_api.routes import docs_ingestion


@pytest.fixture
def service_container():
    container = ApplicationContainer()
    container.config.from_dict({})
    mock_ingestion = Mock()
    container.ingestion_service.override(mock_ingestion)
    container.query_service.override(Mock())
    container.workflow_orchestrator.override(Mock())
    container.token_budget_service.override(Mock())
    container.observability_service.override(Mock())
    container.context_compression_service.override(Mock())
    container.llm_fallback_policy.override(Mock())
    container.job_repository.override(Mock())
    container.ontology_version_service.override(Mock())
    container._ingestion_mock = mock_ingestion
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


def test_docs_ingest_endpoint(client, service_container):
    report = ValidationReport(
        tenant_id="t1",
        is_consistent=True,
        violated_rules=[],
        unsat_classes=[],
        repair_suggestions=[],
        explanation=None,
        ontology_version_id="v1",
    )
    ingestion_mock = service_container._ingestion_mock
    ingestion_mock.process_documents.return_value = report

    resp = client.post(
        "/api/v1/docs-ingest",
        json={
            "files": [{"path": "doc.txt", "content": "hello"}],
            "kg_id": "kg",
            "tenant_id": "t1",
            "ontology_version_id": "v1",
        },
    )

    assert resp.status_code == 200
    assert resp.json()["ontology_version_id"] == "v1"
    ingestion_mock.process_documents.assert_called_once()


def test_docs_ingest_invalid_extension(client, service_container):
    resp = client.post(
        "/api/v1/docs-ingest",
        json={"files": [{"path": "doc.exe", "content": "hello"}]},
    )
    assert resp.status_code == 400
    assert not service_container._ingestion_mock.process_documents.called


def test_docs_ingest_too_large(client, service_container):
    large_content = "a" * (docs_ingestion.MAX_FILE_SIZE + 1)
    resp = client.post(
        "/api/v1/docs-ingest",
        json={"files": [{"path": "doc.txt", "content": large_content}]},
    )
    assert resp.status_code == 400
    assert not service_container._ingestion_mock.process_documents.called
