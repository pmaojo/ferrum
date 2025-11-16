import pytest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from ui_adapters.rest_api.server import app
from ui_adapters.rest_api.dependencies import ApplicationContainer
from domain.entities import ValidationReport


@pytest.fixture
def service_container():
    container = ApplicationContainer()
    container.config.from_dict({})
    container.code_ingestion_service = Mock()
    container.ingestion_service.override(Mock())
    container.query_service.override(Mock())
    container.workflow_orchestrator.override(Mock())
    container.token_budget_service.override(Mock())
    container.observability_service.override(Mock())
    container.context_compression_service.override(Mock())
    container.llm_fallback_policy.override(Mock())
    job_repo = Mock()
    job_repo.get.return_value = {}
    job_repo.update.return_value = None
    job_repo.add.return_value = None
    container.job_repository.override(job_repo)
    container.ontology_version_service.override(Mock())
    return container


@pytest.fixture
def client(service_container):
    with patch(
        "ui_adapters.rest_api.dependencies.create_default_container",
        return_value=service_container,
    ), patch("ui_adapters.rest_api.routes.repo_ingestion.get_db") as db_mock:
        db_mock.return_value.add_job = Mock()
        db_mock.return_value.update_job = Mock()
        with TestClient(app) as c:
            yield c


def test_repo_ingest_endpoint(client, service_container):
    report = ValidationReport(
        is_consistent=True,
        unsat_classes=[],
        repair_suggestions=[],
        tenant_id="t1",
        ontology_version_id="v1",
    )
    service_container.code_ingestion_service.ingest_repository.return_value = report

    resp = client.post(
        "/api/v1/repo-ingest",
        data={"repo_url": "http://example.com/repo", "tenant_id": "t1", "ontology_version_id": "v1"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert "job_id" in data
