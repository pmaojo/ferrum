import logging
import sys
import types
from unittest.mock import MagicMock

import pytest

# Create lightweight stubs to avoid importing full dependencies
kernel_container = types.ModuleType("kernel.container")
ui_settings = types.ModuleType("ui_adapters.rest_api.settings")
ui_dependencies = types.ModuleType("ui_adapters.rest_api.dependencies")
domain_entities = types.ModuleType("domain.entities")

class RestApiSettings:
    pass

class Document:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def resolve(container, name):  # simple stub; overwritten in tests
    """Return a MagicMock for any dependency name.

    The real ``resolve`` function is provided by the application and is
    responsible for returning concrete implementations.  For the purposes of
    these tests we just need a lightweight stub so that the ingestion task
    module can be imported without pulling in the full dependency container.

    The tests replace this stub with ``fake_resolve`` to provide specific
    mock objects as needed.
    """

    return MagicMock()

kernel_container.create_container = MagicMock()
ui_settings.RestApiSettings = RestApiSettings
ui_dependencies.resolve = resolve
domain_entities.Document = Document

sys.modules["kernel.container"] = kernel_container
sys.modules["ui_adapters.rest_api.settings"] = ui_settings
sys.modules["ui_adapters.rest_api.dependencies"] = ui_dependencies
sys.modules["domain.entities"] = domain_entities

import application.tasks.ingestion as ingestion_module
from application.tasks.ingestion import ingest_documents_task


def test_ingest_documents_task_closes_container_on_error(caplog):
    cm = MagicMock()
    container = MagicMock()
    cm.__enter__.return_value = container
    cm.__exit__.return_value = False
    kernel_container.create_container.return_value = cm

    jobs_repo = MagicMock()
    jobs_repo.get.return_value = {"id": "job1"}

    ingestion_service = MagicMock()
    ingestion_service.process_documents.side_effect = RuntimeError("boom")

    def fake_resolve(cont, name):
        if name == "job_repository":
            return jobs_repo
        if name == "ingestion_service":
            return ingestion_service
        return MagicMock()
    ui_dependencies.resolve = fake_resolve
    ingestion_module.resolve = fake_resolve

    with caplog.at_level(logging.INFO):
        with pytest.raises(RuntimeError):
            ingest_documents_task.run(
                "job1", [{"content": "doc"}], "kg1", "tenant1", "v1"
            )

    assert cm.__exit__.called
    assert any(
        r.levelname == "ERROR" and "Ingestion task failed" in r.message
        for r in caplog.records
    )
