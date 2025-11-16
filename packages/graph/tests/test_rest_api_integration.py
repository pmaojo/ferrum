"""Integration tests for REST API endpoints."""

import os
import pytest
pytest.importorskip("fastapi")
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
from types import SimpleNamespace

from domain.entities import OntologyVersion, ScientificDomain

# Import the FastAPI app
from ui_adapters.rest_api.server import app
from ui_adapters.rest_api.dependencies import ApplicationContainer


@pytest.fixture
def test_client(mock_container):
    """Create a test client for the FastAPI app."""
    os.environ["PERMAGRAPH_API_KEY"] = "test-api-key"
    os.environ["TENANT_REGISTRY"] = json.dumps({"test-api-key": "test-tenant"})

    with patch(
        "ui_adapters.rest_api.dependencies.get_container",
        side_effect=lambda *_, **__: mock_container,
    ), patch(
        "ui_adapters.rest_api.dependencies.create_default_container",
        side_effect=lambda *_, **__: mock_container,
    ), patch(
        "application.tasks.ingestion.ingest_documents_task.delay",
        return_value=SimpleNamespace(id="task-id"),
    ):
        with TestClient(app) as client:
            yield client


@pytest.fixture
def mock_container():
    """Create a mock service container."""
    # Create mock services
    mock_ingestion_service = MagicMock()
    mock_query_service = MagicMock()
    mock_workflow_orchestrator = MagicMock()
    mock_token_budget_service = MagicMock()
    mock_observability_service = MagicMock()
    mock_context_compression_service = MagicMock()
    mock_llm_fallback_policy = MagicMock()
    mock_job_repository = MagicMock()
    mock_ontology_version_service = MagicMock()

    job_store: dict[str, dict] = {}
    mock_job_repository.add.side_effect = lambda job: job_store.update(
        {job["job_id"]: job}
    )
    mock_job_repository.get.side_effect = lambda job_id: job_store.get(job_id)
    mock_job_repository.update.side_effect = lambda job: job_store.update(
        {job["job_id"]: job}
    )

    # Configure mock responses
    from domain.entities import ValidationReport

    mock_ingestion_service.process_documents.return_value = ValidationReport(
        tenant_id="test-tenant",
        is_consistent=True,
        violated_rules=[],
        unsat_classes=[],
        repair_suggestions=[],
        explanation=None,
        ontology_version_id="test-version",
    )

    mock_query_service.execute_natural_language_query.return_value = {
        "results": [{"type": "text", "content": "Test result", "relevance_score": 1.0}],
        "metadata": {"error": False, "result_count": 1, "execution_time_ms": 100},
        "explanation": "Test explanation",
    }

    mock_workflow_orchestrator.execute_workflow.return_value = {
        "status": "completed",
        "results": {"step_0": {"status": "completed", "output": "Test output"}},
    }

    mock_token_budget_service.track_usage.return_value = {
        "tenant_id": "test-tenant",
        "tokens": 100,
        "cost_usd": 0.1,
        "model": "test-model",
        "operation_type": "generate",
        "budget_status": {
            "monthly_cost_usd": 0.1,
            "monthly_budget_usd": 100.0,
            "budget_percent": 0.1,
            "alert_triggered": False,
            "budget_exceeded": False,
        },
    }

    mock_observability_service.generate_performance_report.return_value = {
        "tenant_id": "test-tenant",
        "summary": {"total_operations": 10, "success_rate": 1.0},
    }

    # Create container with mock services
    container = ApplicationContainer()
    container.config.from_dict({})
    container.ingestion_service.override(mock_ingestion_service)
    container.query_service.override(mock_query_service)
    container.workflow_orchestrator.override(mock_workflow_orchestrator)
    container.token_budget_service.override(mock_token_budget_service)
    container.observability_service.override(mock_observability_service)
    container.context_compression_service.override(mock_context_compression_service)
    container.llm_fallback_policy.override(mock_llm_fallback_policy)
    container.job_repository.override(mock_job_repository)
    container.ontology_version_service.override(mock_ontology_version_service)

    yield container


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_basic_health_check(self, test_client):
        """Test basic health check endpoint."""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_detailed_health_check(self, test_client, mock_container):
        """Test detailed health check endpoint."""
        response = test_client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert "metrics" in data


class TestIngestEndpoints:
    """Test document ingestion endpoints."""

    def test_synchronous_ingestion(self, test_client, mock_container):
        """Test synchronous document ingestion."""
        # Prepare test data
        test_data = {
            "documents": [
                {"content": "Test document 1"},
                {
                    "content": "Test document 2",
                    "id": "doc-2",
                    "metadata": {"source": "test"},
                },
            ],
            "kg_id": "test-kg",
            "tenant_id": "test-tenant",
            "ontology_version_id": "test-version",
        }

        # Test with API key in header
        response = test_client.post(
            "/api/ingest", json=test_data, headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_consistent"] is True
        assert data["tenant_id"] == "test-tenant"

        # Verify service was called with correct parameters
        mock_container.ingestion_service.process_documents.assert_called_once()
        call_kwargs = (
            mock_container.ingestion_service.process_documents.call_args.kwargs
        )
        assert call_kwargs["kg_id"] == "test-kg"
        assert call_kwargs["tenant_id"] == "test-tenant"
        assert call_kwargs["ontology_version_id"] == "test-version"
        assert len(call_kwargs["documents"]) == 2

    def test_async_ingestion(self, test_client, mock_container):
        """Test asynchronous document ingestion."""
        # Prepare test data
        test_data = {
            "documents": [
                {"content": "Test document 1"},
                {"content": "Test document 2"},
            ],
            "kg_id": "test-kg",
            "tenant_id": "test-tenant",
        }

        # Test with Bearer token
        response = test_client.post(
            "/api/v1/ingest/async",
            json=test_data,
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "job_id" in data
        assert "created_at" in data

        # Test job status endpoint
        job_id = data["job_id"]
        response = test_client.get(
            f"/api/v1/jobs/{job_id}", headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "queued"
        assert data["progress"] == 0.0


class TestQueryEndpoints:
    """Test query endpoints."""

    def test_query_execution(self, test_client, mock_container):
        """Test query execution."""
        # Prepare test data
        test_data = {
            "question": "What is GraphRAG?",
            "kg_id": "test-kg",
            "tenant_id": "test-tenant",
            "include_explanation": True,
            "include_subgraph": True,
        }

        # Test query endpoint
        response = test_client.post(
            "/api/query", json=test_data, headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "metadata" in data
        assert "explanation" in data
        assert not data["metadata"]["error"]

        # Verify service was called with correct parameters
        mock_container.query_service.execute_natural_language_query.assert_called_once()
        call_kwargs = (
            mock_container.query_service.execute_natural_language_query.call_args.kwargs
        )
        assert call_kwargs["question"] == "What is GraphRAG?"
        assert call_kwargs["kg_id"] == "test-kg"
        assert call_kwargs["tenant_id"] == "test-tenant"
        assert call_kwargs["include_explanation"] is True
        assert call_kwargs["include_subgraph"] is True

    def test_versioned_query_with_caching(self, test_client, mock_container):
        """Test versioned query endpoint with caching."""
        # Prepare test data
        test_data = {
            "question": "What is GraphRAG?",
            "kg_id": "test-kg",
            "tenant_id": "test-tenant",
        }

        # First request should call the service
        response = test_client.post(
            "/api/v1/query", json=test_data, headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 200

        # Reset mock to verify second call doesn't hit the service
        mock_container.query_service.execute_natural_language_query.reset_mock()

        # Second request with same parameters should use cache
        response = test_client.post(
            "/api/v1/query", json=test_data, headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 200
        # Service should not be called again due to caching
        mock_container.query_service.execute_natural_language_query.assert_not_called()


class TestWorkflowEndpoints:
    """Test workflow endpoints."""

    def test_workflow_registration(self, test_client, mock_container):
        """Test workflow registration."""
        # Prepare test data
        test_data = {
            "workflow_id": "test-workflow",
            "steps": [{"type": "graphrag_query", "question": "What is GraphRAG?"}],
            "framework": "test-framework",
            "tenant_id": "test-tenant",
        }

        # Test workflow registration
        response = test_client.post(
            "/api/workflows/register",
            json=test_data,
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "test-workflow"
        assert data["status"] == "registered"

        # Verify service was called with correct parameters
        mock_container.workflow_orchestrator.register_workflow.assert_called_once()
        call_kwargs = (
            mock_container.workflow_orchestrator.register_workflow.call_args.kwargs
        )
        assert call_kwargs["workflow_id"] == "test-workflow"
        assert call_kwargs["framework"] == "test-framework"
        assert call_kwargs["tenant_id"] == "test-tenant"
        assert len(call_kwargs["steps"]) == 1

    def test_workflow_execution(self, test_client, mock_container):
        """Test workflow execution."""
        # Prepare test data
        test_data = {
            "workflow_id": "test-workflow",
            "input_data": {"key": "value"},
            "tenant_id": "test-tenant",
        }

        # Test workflow execution
        response = test_client.post(
            "/api/workflows/execute",
            json=test_data,
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "results" in data

        # Verify service was called with correct parameters
        mock_container.workflow_orchestrator.execute_workflow.assert_called_once()
        call_kwargs = (
            mock_container.workflow_orchestrator.execute_workflow.call_args.kwargs
        )
        assert call_kwargs["workflow_id"] == "test-workflow"
        assert call_kwargs["input_data"] == {"key": "value"}
        assert call_kwargs["tenant_id"] == "test-tenant"


class TestTokenBudgetEndpoints:
    """Test token budget endpoints."""

    def test_track_usage(self, test_client, mock_container):
        """Test token usage tracking."""
        # Prepare test data
        test_data = {
            "tenant_id": "test-tenant",
            "tokens": 100,
            "model": "test-model",
            "operation_type": "generate",
        }

        # Test token usage tracking
        response = test_client.post(
            "/api/token-budget/track",
            json=test_data,
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant"
        assert data["tokens"] == 100
        assert data["model"] == "test-model"
        assert "budget_status" in data

        # Verify service was called with correct parameters
        mock_container.token_budget_service.track_usage.assert_called_once()
        call_kwargs = mock_container.token_budget_service.track_usage.call_args.kwargs
        assert call_kwargs["tenant_id"] == "test-tenant"
        assert call_kwargs["tokens"] == 100
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["operation_type"] == "generate"

    def test_get_usage(self, test_client, mock_container):
        """Test getting token usage."""
        # Configure mock response
        mock_container.token_budget_service.get_tenant_usage.return_value = {
            "tenant_id": "test-tenant",
            "month": "2025-07",
            "total_tokens": 1000,
            "total_cost_usd": 1.0,
            "operations": {},
            "models": {},
        }

        # Test get usage endpoint
        response = test_client.get(
            "/api/token-budget/test-tenant", headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant"
        assert data["total_tokens"] == 1000
        assert data["total_cost_usd"] == 1.0

        # Verify service was called with correct parameters
        mock_container.token_budget_service.get_tenant_usage.assert_called_once_with(
            tenant_id="test-tenant"
        )

    def test_set_budget(self, test_client, mock_container):
        """Test setting token budget."""
        # Prepare test data
        test_data = {
            "tenant_id": "test-tenant",
            "monthly_budget_usd": 200.0,
            "alert_threshold_percent": 75.0,
            "enable_degradation": True,
        }

        # Configure mock response
        mock_container.token_budget_service.set_tenant_budget.return_value = {
            "tenant_id": "test-tenant",
            "monthly_budget_usd": 200.0,
            "alert_threshold_percent": 75.0,
            "enable_degradation": True,
        }

        # Test set budget endpoint
        response = test_client.post(
            "/api/token-budget/budget",
            json=test_data,
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant"
        assert data["monthly_budget_usd"] == 200.0
        assert data["alert_threshold_percent"] == 75.0
        assert data["enable_degradation"] is True

        # Verify service was called with correct parameters
        mock_container.token_budget_service.set_tenant_budget.assert_called_once()
        call_kwargs = (
            mock_container.token_budget_service.set_tenant_budget.call_args.kwargs
        )
        assert call_kwargs["tenant_id"] == "test-tenant"
        assert call_kwargs["monthly_budget_usd"] == 200.0
        assert call_kwargs["alert_threshold_percent"] == 75.0
        assert call_kwargs["enable_degradation"] is True


class TestOntologyVersionEndpoints:
    """Test ontology version management endpoints."""

    def test_store_version(self, test_client, mock_container):
        mock_container.ontology_version_service.store_version.return_value = (
            OntologyVersion(
                id="v1",
                checksum="cs",
                parent_version=None,
                tenant_id="test-tenant",
                domain=ScientificDomain.GENERAL,
                created_at=datetime.utcnow(),
                axioms=["A"],
            )
        )
        payload = {
            "triples": [{"subject": "s", "predicate": "p", "object": "o"}],
            "tenant_id": "test-tenant",
        }
        response = test_client.post(
            "/api/ontology/versions",
            json=payload,
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        mock_container.ontology_version_service.store_version.assert_called_once()

    def test_get_version(self, test_client, mock_container):
        mock_container.ontology_version_service.get_version.return_value = (
            OntologyVersion(
                id="v1",
                checksum="cs",
                parent_version=None,
                tenant_id="test-tenant",
                domain=ScientificDomain.GENERAL,
                created_at=datetime.utcnow(),
                axioms=["A"],
            )
        )
        response = test_client.get(
            "/api/ontology/versions/v1?tenant_id=test-tenant",
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        mock_container.ontology_version_service.get_version.assert_called_once_with(
            version_id="v1", tenant_id="test-tenant"
        )

    def test_list_versions(self, test_client, mock_container):
        mock_container.ontology_version_service.get_version_history.return_value = []
        response = test_client.get(
            "/api/ontology/versions?tenant_id=test-tenant",
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        mock_container.ontology_version_service.get_version_history.assert_called_once_with(
            tenant_id="test-tenant", limit=10
        )

    def test_delete_version(self, test_client, mock_container):
        mock_container.ontology_version_service.delete_version.return_value = True
        response = test_client.delete(
            "/api/ontology/versions/v1?tenant_id=test-tenant",
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        mock_container.ontology_version_service.delete_version.assert_called_once_with(
            version_id="v1", tenant_id="test-tenant"
        )


class TestMonitoringEndpoints:
    """Test monitoring endpoints."""

    def test_metrics_endpoint(self, test_client):
        """Test Prometheus metrics endpoint."""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_performance_metrics(self, test_client, mock_container):
        """Test performance metrics endpoint."""
        response = test_client.get(
            "/api/metrics?tenant_id=test-tenant", headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant"
        assert "summary" in data

        # Verify service was called with correct parameters
        mock_container.observability_service.generate_performance_report.assert_called_once_with(
            tenant_id="test-tenant"
        )


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_api_key(self, test_client):
        """Test invalid API key handling."""
        payload = {
            "tenant_id": "test-tenant",
            "customer_id": "c1",
            "event_type": "ecommerce.purchase",
            "event_data": {},
        }
        response = test_client.post(
            "/api/v1/ecommerce/track-event",
            json=payload,
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "HTTP_401"

    def test_not_found_endpoint(self, test_client):
        """Test 404 error handling."""
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "HTTP_404"
        assert "suggestions" in data

    def test_validation_error(self, test_client):
        """Test validation error handling."""
        # Send invalid request body
        response = test_client.post(
            "/api/query",
            json={},  # Missing required fields
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 422  # Unprocessable Entity

    def test_graphrag_exception_handling(self, test_client, mock_container):
        """Test GraphRAGException handling."""
        # Configure mock to raise exception
        from domain.services import GraphRAGException

        mock_container.query_service.execute_natural_language_query.side_effect = (
            GraphRAGException(
                message="Test error",
                error_code="TEST_ERROR",
                context={"test": "context"},
            )
        )

        # Test query endpoint with error
        response = test_client.post(
            "/api/query",
            json={"question": "Test question"},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "TEST_ERROR"
        assert data["message"] == "Test error"
        assert data["context"] == {"test": "context"}
        assert "suggestions" in data


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
