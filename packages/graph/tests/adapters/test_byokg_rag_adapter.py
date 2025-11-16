import pytest
pytest.importorskip("numpy")
from unittest.mock import MagicMock

from adapters.retrievers.byokg_rag_adapter import ByoKGRAGAdapter
from domain.entities import Triple
from domain.services import GraphRAGException


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    return engine


def test_index_invokes_engine_and_returns_triples(mock_engine):
    mock_engine.ingest.return_value = {
        "triples": [
            {"subject": "s", "predicate": "p", "object": "o"}
        ]
    }
    adapter = ByoKGRAGAdapter(engine=mock_engine)

    result = adapter.index(docs=["doc"], kg_id="kg", tenant_id="tenant")

    mock_engine.ingest.assert_called_once_with(docs=["doc"], kg_id="kg", tenant_id="tenant")
    assert result == [Triple("s", "p", "o", "tenant")]


def test_run_invokes_engine_query(mock_engine):
    mock_engine.query.return_value = {"answer": "42"}
    adapter = ByoKGRAGAdapter(engine=mock_engine)

    result = adapter.run(question="q", kg_id="kg", tenant_id="tenant")

    mock_engine.query.assert_called_once_with(question="q", kg_id="kg", tenant_id="tenant")
    assert result == "42"


def test_run_returns_triples_when_option_enabled(mock_engine):
    mock_engine.query.return_value = {
        "triples": [
            {"subject": "a", "predicate": "b", "object": "c"}
        ]
    }
    adapter = ByoKGRAGAdapter(engine=mock_engine)

    result = adapter.run(question="q", kg_id="kg", tenant_id="tenant", opts={"return_triples": True})

    assert result == [Triple("a", "b", "c", "tenant")]


def test_index_error_propagation(mock_engine):
    mock_engine.ingest.side_effect = RuntimeError("boom")
    adapter = ByoKGRAGAdapter(engine=mock_engine)

    with pytest.raises(GraphRAGException):
        adapter.index(docs=["doc"], kg_id="kg", tenant_id="tenant")


def test_run_error_propagation(mock_engine):
    mock_engine.query.side_effect = RuntimeError("boom")
    adapter = ByoKGRAGAdapter(engine=mock_engine)

    with pytest.raises(GraphRAGException):
        adapter.run(question="q", kg_id="kg", tenant_id="tenant")
