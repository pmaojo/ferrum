import os
import pathlib
import uuid
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.storage import SQLAlchemyIngestionRepository, RepositoryIngestionModel, Base
from fastapi import FastAPI
import importlib
import types
from pathlib import Path as _Path
from types import SimpleNamespace

_pkg = types.ModuleType("ui_adapters.rest_api")
_pkg.__path__ = [str(_Path(__file__).parents[2] / "ui_adapters/rest_api")]
sys.modules.setdefault("ui_adapters.rest_api", _pkg)
ingestion_route = importlib.import_module("ui_adapters.rest_api.routes.ingestion")
from ui_adapters.rest_api.dependencies import ApplicationContainer
from dependency_injector import providers
from unittest.mock import patch
from adapters.inmemory_tracing_adapter import InMemoryTracingAdapter
from adapters.numpy_vector_math import NumpyVectorMathAdapter
from adapters.simple_query_translator_adapter import SimpleQueryTranslatorAdapter
from domain.ingestion_service import IngestionService
from domain.query_service import QueryService
from domain.workflow_orchestrator import WorkflowOrchestrator
from domain.token_budget_service import TokenBudgetService
from domain.context_compression_service import ContextCompressionService
from domain.llm_fallback_policy import LLMFallbackPolicy
from tests.integration.test_user_journey_e2e import (
    InMemoryGraphRetriever,
    SimpleValidator,
    DummyObservabilityService,
)
from application.tasks.ingestion import ingest_documents_task
from domain.entities import Document


@pytest.fixture()
def client(tmp_path: pathlib.Path):
    db_url = "sqlite:///" + str(tmp_path / "test.db")
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    repo = SQLAlchemyIngestionRepository(Session())

    retriever = InMemoryGraphRetriever()
    validator = SimpleValidator()
    tracer = InMemoryTracingAdapter()
    translator = SimpleQueryTranslatorAdapter()
    ingestion = IngestionService(
        retriever=retriever,
        validator=validator,
        tracer=tracer,
    )
    query = QueryService(translator=translator, retriever=retriever, tracer=tracer)
    orchestrator = WorkflowOrchestrator(retriever=retriever, translator=translator, tracer=tracer)
    token_budget = TokenBudgetService(tracer=tracer, storage_path=str(tmp_path))
    observability = DummyObservabilityService()
    compression = ContextCompressionService(
        llm=None,
        tracer=tracer,
        vector_math=NumpyVectorMathAdapter(),
        use_embeddings=False,
        important_keywords=None,
    )
    llm_policy = LLMFallbackPolicy(primary_llm=None, fallback_llm=None, tracer=tracer)

    container = ApplicationContainer()
    container.config.from_dict({"job_repository_url": db_url})
    container.ingestion_service.override(providers.Object(ingestion))
    container.ingestion_service = ingestion
    container.query_service.override(providers.Object(query))
    container.workflow_orchestrator.override(providers.Object(orchestrator))
    container.token_budget_service.override(providers.Object(token_budget))
    container.observability_service.override(providers.Object(observability))
    container.context_compression_service.override(providers.Object(compression))
    container.llm_fallback_policy.override(providers.Object(llm_policy))
    container.job_repository.override(providers.Object(repo))
    container.job_repository = repo
    container.ontology_version_service.override(SimpleValidator())

    app = FastAPI()
    app.include_router(ingestion_route.router)
    app.state.container = container
    with patch(
        "application.tasks.ingestion.create_container",
        return_value=container,
    ), patch(
        "application.tasks.ingestion.ingest_documents_task.delay",
        return_value=SimpleNamespace(id="task-id"),
    ):
        with TestClient(app) as c:
            yield c, repo, Session


def test_ingestion_job_persisted(client):
    client_app, repo, Session = client
    headers = {"X-API-Key": "test-key"}
    os.environ["PERMAGRAPH_API_KEY"] = "test-key"

    docs = [{"content": "Alice works at ACME."}]
    payload = {
        "documents": docs,
        "kg_id": "repo1",
        "tenant_id": "t1",
        "ontology_version_id": "v1",
    }
    resp = client_app.post("/api/v1/ingest/async", json=payload, headers=headers)
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    document_models = [
        Document(
            id=str(uuid.uuid4()),
            content=d["content"],
            metadata={},
            processed_at=None,
            extraction_status="pending",
            tenant_id="t1",
        )
        for d in docs
    ]
    ingest_documents_task.apply(
        args=[
            job_id,
            [d.__dict__ for d in document_models],
            "repo1",
            "t1",
            "v1",
        ]
    )

    db = Session()
    record = db.get(RepositoryIngestionModel, job_id)
    assert record is not None
    assert record.status == "completed"
    assert record.result_path
    assert pathlib.Path(record.result_path).exists()
