import asyncio
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def ingestion_module(service_container):
    # Stub dependencies module
    deps = types.ModuleType("ui_adapters.rest_api.dependencies")
    class DummyContainer:  # minimal container
        pass
    deps.ServiceContainer = DummyContainer
    deps.get_container = lambda: service_container
    sys.modules.setdefault("ui_adapters", types.ModuleType("ui_adapters"))
    sys.modules.setdefault("ui_adapters.rest_api", types.ModuleType("ui_adapters.rest_api"))
    sys.modules["ui_adapters.rest_api.dependencies"] = deps

    # Stub fastapi module to avoid heavy dependencies
    fastapi_stub = types.ModuleType("fastapi")
    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass
        def post(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def get(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    def Depends(x):
        return x
    class BackgroundTasks: ...
    class HTTPException(Exception): ...
    class Request: ...
    fastapi_stub.APIRouter = APIRouter
    fastapi_stub.Depends = Depends
    fastapi_stub.BackgroundTasks = BackgroundTasks
    fastapi_stub.HTTPException = HTTPException
    fastapi_stub.Request = Request
    sys.modules["fastapi"] = fastapi_stub

    # Stub models module with minimal classes used by ingestion
    models = types.ModuleType("ui_adapters.rest_api.models")
    class IngestDocument:
        def __init__(self, *, content: str, id: str | None = None, metadata: dict | None = None):
            self.content = content
            self.id = id
            self.metadata = metadata or {}
    class IngestRequest:
        def __init__(self, *, documents, kg_id="kg", tenant_id="t1", ontology_version_id="v1"):
            self.documents = documents
            self.kg_id = kg_id
            self.tenant_id = tenant_id
            self.ontology_version_id = ontology_version_id
    class ValidationReportModel:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class AsyncJobResponse: ...
    class JobStatusResponse: ...
    models.IngestDocument = IngestDocument
    models.IngestRequest = IngestRequest
    models.ValidationReportModel = ValidationReportModel
    models.AsyncJobResponse = AsyncJobResponse
    models.JobStatusResponse = JobStatusResponse
    sys.modules["ui_adapters.rest_api.models"] = models

    # Load ingestion route module
    path = (
        Path(__file__).resolve().parents[2]
        / "ui_adapters"
        / "rest_api"
        / "routes"
        / "ingestion.py"
    )
    spec = importlib.util.spec_from_file_location("ingestion_route", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    module.IngestDocument = models.IngestDocument
    module.IngestRequest = models.IngestRequest
    return module


@pytest.fixture
def service_container():
    class Container:
        pass
    container = Container()
    ingestion_mock = Mock()
    container.ingestion_service = ingestion_mock
    container._ingestion_mock = ingestion_mock
    return container


def test_ingest_ferrus_requirements(ingestion_module, service_container):
    class FakeReport:
        def __init__(self):
            self.is_consistent = True
            self.unsat_classes = []
            self.repair_suggestions = []
            self.tenant_id = "t1"
            self.ontology_version_id = "v1"
        def _asdict(self):
            return self.__dict__

    ingestion_mock = service_container._ingestion_mock
    ingestion_mock.validate_triples.return_value = FakeReport()

    content = """---
id: REQ-1
code_links:
  - src/modules/auth/usecases/login.rs
---
Body
"""
    req = ingestion_module.IngestRequest(
        documents=[ingestion_module.IngestDocument(content=content, metadata={"path": "req.md"})],
        kg_id="kg",
        tenant_id="t1",
        ontology_version_id="v1",
    )
    result = asyncio.run(ingestion_module._handle_ingestion(req, service_container))
    assert result.ontology_version_id == "v1"
    ingestion_mock.validate_triples.assert_called_once()
    triples = ingestion_mock.validate_triples.call_args.kwargs["triples"]
    assert triples[0].subject == "http://ferrus.io/ontology#Requirement.REQ-1"
    assert triples[0].object == "http://ferrus.io/ontology#auth.UseCase.Login"
