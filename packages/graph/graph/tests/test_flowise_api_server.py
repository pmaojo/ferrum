import pytest
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from ui_adapters.flowise.api_server import app, get_flowise_adapter
from application.ports import FlowiseAdapterPort


def test_query_endpoint_di():
    adapter = MagicMock(spec=FlowiseAdapterPort)
    adapter.query_knowledge_graph.return_value = {"ok": True}
    app.state.adapter = adapter
    app.dependency_overrides[get_flowise_adapter] = lambda: adapter
    with TestClient(app) as client:
        resp = client.post("/api/graphrag/query", json={"question": "hi"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        adapter.query_knowledge_graph.assert_called_once()
    app.dependency_overrides.clear()
    delattr(app.state, "adapter")


def test_index_endpoint_di():
    adapter = MagicMock(spec=FlowiseAdapterPort)
    adapter.index_documents.return_value = {"count": 1}
    app.state.adapter = adapter
    app.dependency_overrides[get_flowise_adapter] = lambda: adapter
    with TestClient(app) as client:
        resp = client.post(
            "/api/graphrag/index",
            json={"docs": ["a"], "kg_id": "kg", "tenant_id": "t"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"count": 1}
        adapter.index_documents.assert_called_once()
    app.dependency_overrides.clear()
    delattr(app.state, "adapter")
