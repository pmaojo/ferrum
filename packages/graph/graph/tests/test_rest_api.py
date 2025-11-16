import pytest
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from ui_adapters.rest_api.server import app
from ui_adapters.rest_api.dependencies import (
    ApplicationContainer,
    get_container,
    get_llm,
)

from domain.entities import ValidationReport, Triple


@pytest.fixture
def service_container():
    container = ApplicationContainer()
    container.config.from_dict({})

    container.ingestion_service.override(Mock())
    container.query_service.override(Mock())
    container.workflow_orchestrator.override(Mock())
    container.token_budget_service.override(Mock())
    container.observability_service.override(Mock())
    container.context_compression_service.override(Mock())
    container.llm_fallback_policy.override(Mock())
    container.job_repository.override(Mock())
    container.ontology_version_service.override(Mock())

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


def test_ingest_endpoint(client, service_container):
    report = ValidationReport(
        tenant_id="t1",
        is_consistent=True,
        violated_rules=[],
        unsat_classes=[],
        repair_suggestions=[],
        explanation=None,
        ontology_version_id="v1",
    )
    container_ingestion = service_container.ingestion_service()
    container_ingestion.process_documents.return_value = report

    resp = client.post(
        "/api/ingest",
        json={
            "documents": [{"content": "doc"}],
            "kg_id": "kg",
            "tenant_id": "t1",
            "ontology_version_id": "v1",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ontology_version_id"] == "v1"
    container_ingestion.process_documents.assert_called_once()


def test_query_endpoint(client, service_container):
    container_query = service_container.query_service()
    container_query.execute_natural_language_query.return_value = {
        "result": "ok"
    }
    resp = client.post(
        "/api/query",
        json={"question": "q", "kg_id": "kg", "tenant_id": "t", "user_id": "u"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"result": "ok"}
    container_query.execute_natural_language_query.assert_called_once()


def test_workflow_register_and_execute(client, service_container):
    container_wf = service_container.workflow_orchestrator()
    container_wf.execute_workflow.return_value = {
        "status": "done"
    }
    register_resp = client.post(
        "/api/workflows/register",
        json={"workflow_id": "wf", "steps": [], "framework": "f", "tenant_id": "t"},
    )
    assert register_resp.status_code == 200
    execute_resp = client.post(
        "/api/workflows/execute",
        json={"workflow_id": "wf", "input_data": {}, "tenant_id": "t"},
    )
    assert execute_resp.status_code == 200
    assert execute_resp.json() == {"status": "done"}
    container_wf.register_workflow.assert_called_once()
    container_wf.execute_workflow.assert_called_once()


def test_metrics_and_health(client, service_container):
    container_obs = service_container.observability_service()
    container_obs.generate_performance_report.return_value = {
        "ok": True
    }
    m_resp = client.get("/api/metrics", params={"tenant_id": "t"})
    h_resp = client.get("/api/health")
    assert m_resp.status_code == 200
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "ok"
    container_obs.generate_performance_report.assert_called_once_with(
        tenant_id="t"
    )


def test_token_budget_endpoints(client, service_container):
    container_budget = service_container.token_budget_service()
    container_budget.track_usage.return_value = {"tracked": True}
    container_budget.get_tenant_usage.return_value = {
        "tenant_id": "t"
    }
    container_budget.set_tenant_budget.return_value = {
        "tenant_id": "t",
        "monthly_budget_usd": 1,
    }

    track_resp = client.post(
        "/api/token-budget/track",
        json={
            "tenant_id": "t",
            "tokens": 10,
            "model": "m",
            "operation_type": "generate",
        },
    )
    usage_resp = client.get("/api/token-budget/t")
    set_resp = client.post(
        "/api/token-budget/budget",
        json={"tenant_id": "t", "monthly_budget_usd": 1},
    )

    assert track_resp.status_code == 200
    assert usage_resp.status_code == 200
    assert set_resp.status_code == 200
    container_budget.track_usage.assert_called_once()
    container_budget.get_tenant_usage.assert_called_once_with(
        tenant_id="t"
    )
    container_budget.set_tenant_budget.assert_called_once()
