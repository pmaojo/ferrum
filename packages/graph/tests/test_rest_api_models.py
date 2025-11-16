import pytest
from pydantic import ValidationError
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "rest_models",
    Path(__file__).resolve().parents[1]
    / "ui_adapters"
    / "rest_api"
    / "models.py",
)
rest_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rest_models)

IngestRequest = rest_models.IngestRequest
IngestDocument = rest_models.IngestDocument
AsyncJobResponse = rest_models.AsyncJobResponse
JobStatusResponse = rest_models.JobStatusResponse
ValidationReportModel = rest_models.ValidationReportModel
TokenUsageRequest = rest_models.TokenUsageRequest
SetBudgetRequest = rest_models.SetBudgetRequest
WorkflowRegisterRequest = rest_models.WorkflowRegisterRequest
WorkflowExecuteRequest = rest_models.WorkflowExecuteRequest
RepoIngestRequest = rest_models.RepoIngestRequest


def test_ingest_request_defaults():
    req = IngestRequest(
        documents=[{"content": "doc"}],
        kg_id="kg1",
        tenant_id="tenant1",
    )

    assert req.kg_id == "kg1"
    assert req.tenant_id == "tenant1"
    assert req.ontology_version_id == "default"
    assert req.documents[0].content == "doc"
    assert req.documents[0].metadata == {}


def test_async_job_response_serialization():
    resp = AsyncJobResponse(
        job_id="job",
        status="queued",
        created_at="0",
        estimated_completion="1",
    )
    data = resp.model_dump()
    assert data["job_id"] == "job"
    assert data["status"] == "queued"


def test_job_status_response_validation():
    status = JobStatusResponse(
        job_id="j",
        status="processing",
        progress=0.4,
        created_at=1.0,
        updated_at=2.0,
    )
    assert status.progress == 0.4
    with pytest.raises(ValidationError):
        JobStatusResponse(
            job_id="j",
            status="processing",
            progress=1.5,
            created_at=1.0,
            updated_at=2.0,
        )


def test_validation_report_model():
    report = ValidationReportModel(
        is_consistent=True,
        unsat_classes=[],
        repair_suggestions=[],
        tenant_id="t",
        ontology_version_id="v1",
    )
    assert report.tenant_id == "t"
    assert report.ontology_version_id == "v1"


def test_token_usage_request_defaults():
    req = TokenUsageRequest(
        tenant_id="t",
        tokens=10,
        model="m",
        operation_type="generate",
    )
    assert req.cost_usd is None
    assert req.metadata is None


def test_set_budget_request_partial():
    req = SetBudgetRequest(tenant_id="t", monthly_budget_usd=10.0)
    assert req.alert_threshold_percent is None
    assert req.enable_degradation is None


def test_workflow_register_request_parsing():
    req = WorkflowRegisterRequest(
        workflow_id="wf",
        steps=[{"type": "test"}],
        framework="f",
        tenant_id="t",
    )
    assert req.workflow_id == "wf"
    assert req.steps[0]["type"] == "test"
    assert req.framework == "f"


def test_workflow_execute_request_parsing():
    req = WorkflowExecuteRequest(
        workflow_id="wf",
        input_data={"k": "v"},
        tenant_id="t",
    )
    assert req.input_data == {"k": "v"}


def test_repo_ingest_request_defaults():
    req = RepoIngestRequest(repo_url="http://example.com")
    assert req.repo_url == "http://example.com"
    assert req.tenant_id == "default"
    assert req.ontology_version_id == "default"
