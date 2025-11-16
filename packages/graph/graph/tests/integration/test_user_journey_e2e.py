import os
import logging
import re
import pathlib
from typing import Any, Dict, List, Union
from unittest.mock import Mock

import pytest
pytest.importorskip("fastapi")
pytest.importorskip("numpy")
from fastapi.testclient import TestClient
from domain.entities import Triple, ValidationReport
from domain.ingestion_service import IngestionService
from domain.query_service import QueryService
from domain.workflow_orchestrator import WorkflowOrchestrator
from domain.token_budget_service import TokenBudgetService
from domain.context_compression_service import ContextCompressionService
from domain.llm_fallback_policy import LLMFallbackPolicy
from adapters.simple_query_translator_adapter import SimpleQueryTranslatorAdapter
from adapters.numpy_vector_math import NumpyVectorMathAdapter


class InMemoryGraphRetriever:
    def __init__(self) -> None:
        self.storage: Dict[tuple[str, str], List[Triple]] = {}

    def index(self, *, docs: List[str], kg_id: str, tenant_id: str) -> List[Triple]:
        triples: List[Triple] = []
        pattern = re.compile(r"(\w+) works at (\w+)", re.IGNORECASE)
        for doc in docs:
            for subj, obj in pattern.findall(doc):
                triples.append(Triple(subj, "worksAt", obj, tenant_id))
        self.storage.setdefault((tenant_id, kg_id), []).extend(triples)
        return triples

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Union[Dict[str, Any], None] = None,
    ) -> str:
        triples = self.storage.get((tenant_id, kg_id), [])
        match = re.search(r"Who works at (\w+)", question)
        if match:
            company = match.group(1)
            people = [t.subject for t in triples if t.object.lower() == company.lower()]
            if people:
                return ", ".join(people) + f" work at {company}."
        return "No results."


class SimpleValidator:
    def validate(
        self, *, triples: List[Triple], ontology_version_id: str
    ) -> ValidationReport:
        return ValidationReport(True, [], [], "tenant", ontology_version_id)

    def validate_delta(
        self, *, new_triples: List[Triple], existing_version_id: str, tenant_id: str
    ) -> ValidationReport:
        return ValidationReport(True, [], [], tenant_id, existing_version_id)

    def convert_to_owl(self, *, triples: List[Triple]) -> str:
        return ""


class DummyObservabilityService:
    def generate_performance_report(
        self, *, tenant_id: str, time_range_hours: int = 24
    ) -> Dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "summary": {"total_operations": 0, "success_rate": 1.0},
        }

    def record_operation_metrics(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_validation_metrics(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_graph_metrics(self, *args: Any, **kwargs: Any) -> None:
        pass


@pytest.fixture()
def service_container(tmp_path: pathlib.Path):
    from ui_adapters.rest_api.dependencies import ApplicationContainer, MockTracingAdapter
    from adapters.inmemory_tracing_adapter import InMemoryTracingAdapter

    retriever = InMemoryGraphRetriever()
    validator = SimpleValidator()
    tracer = InMemoryTracingAdapter()
    translator = SimpleQueryTranslatorAdapter()
    ingestion = IngestionService(
        retriever=retriever,
        validator=validator,
        tracer=tracer,
        logger=logging.getLogger("test.ingestion_service"),
    )
    query = QueryService(translator=translator, retriever=retriever, tracer=tracer)
    orchestrator = WorkflowOrchestrator(
        retriever=retriever, translator=translator, tracer=tracer
    )
    token_budget = TokenBudgetService(tracer=tracer, storage_path=str(tmp_path))
    observability = DummyObservabilityService()
    compression = ContextCompressionService(
        llm=None,
        tracer=tracer,
        vector_math=NumpyVectorMathAdapter(),
        use_embeddings=False,
        important_keywords={"john", "age", "name", "lives", "city", "population"},
        logger=logging.getLogger("test.context_compression_service"),
    )
    llm_policy = LLMFallbackPolicy(primary_llm=None, fallback_llm=None, tracer=tracer)
    container = ApplicationContainer()
    container.config.from_dict({})
    container.ingestion_service.override(ingestion)
    container.query_service.override(query)
    container.workflow_orchestrator.override(orchestrator)
    container.token_budget_service.override(token_budget)
    container.observability_service.override(observability)
    container.context_compression_service.override(compression)
    container.llm_fallback_policy.override(llm_policy)
    container.job_repository.override(Mock())
    container.ontology_version_service.override(Mock())
    return container


@pytest.fixture()
def client(service_container):
    from ui_adapters.rest_api import server

    os.environ["PERMAGRAPH_API_KEY"] = "test-key"
    server.app.state.container = service_container
    with TestClient(server.app) as c:
        yield c
    server.app.state.container = None


def test_full_user_journey(client: TestClient):
    headers = {"X-API-Key": "test-key"}

    resp = client.get("/api/health")
    assert resp.status_code == 200

    docs = [
        {"content": "Alice works at TechCorp."},
        {"content": "Bob works at TechCorp."},
    ]
    ingest_payload = {
        "documents": docs,
        "kg_id": "kg1",
        "tenant_id": "t1",
        "ontology_version_id": "v1",
    }
    resp = client.post(
        "/api/v1/ingest",
        json={
            "documents": docs,
            "kg_id": "kg1",
            "tenant_id": "t1",
            "ontology_version_id": "v1",
        },
        headers=headers,
    )

    query_payload = {
        "question": "Who works at TechCorp?",
        "kg_id": "kg1",
        "tenant_id": "t1",
        "user_id": "u1",
    }
    resp = client.post(
        "/api/v1/ingest",
        json={
            "documents": docs,
            "kg_id": "kg1",
            "tenant_id": "t1",
            "ontology_version_id": "v1",
        },
        headers=headers,
    )
    query_payload = {
        "question": "Who works at TechCorp?",
        "kg_id": "kg1",
        "tenant_id": "t1",
        "user_id": "u1",
    }
    resp = client.post("/api/query", json=query_payload, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/token-budget/t1", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/metrics", params={"tenant_id": "t1"}, headers=headers)
    assert resp.status_code == 200
