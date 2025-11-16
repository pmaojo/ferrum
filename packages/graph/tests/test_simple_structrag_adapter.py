import types
import pathlib
import pytest

module = types.ModuleType("simple_structrag_adapter")
exec((pathlib.Path(__file__).resolve().parents[1] / "adapters" / "structrag" / "simple_structrag_adapter.py").read_text(), module.__dict__)
SimpleStructRAGAdapter = module.SimpleStructRAGAdapter


@pytest.fixture
def adapter():
    return SimpleStructRAGAdapter()


def test_select_structure_table(adapter):
    query = "What is the average score?"
    assert adapter.select_structure(query=query, documents=[], tenant_id="t1") == "table"


def test_decompose_question(adapter):
    query = "What is the capital of France and who is the president?"
    assert adapter.decompose_question(query=query, documents=[], tenant_id="t1") == [
        "What is the capital of France",
        "who is the president",
    ]


def test_structurize_list(adapter):
    docs = ["Item A", "Item B"]
    result = adapter.structurize(
        documents=docs, structure_type="list", tenant_id="t1", data_id="d1"
    )
    assert result == "- Item A\n- Item B"


def test_generate_router_training_data(adapter):
    docs = [
        "Average income report\nNumbers: 10 20",
        "Connections overview\nA related to B",
    ]
    data = adapter.generate_router_training_data(documents=docs, tenant_id="tenant")
    assert data == [
        {"query": "Average income report", "structure": "table"},
        {"query": "Connections overview", "structure": "graph"},
    ]


def test_multi_hop_answer(adapter):
    docs = ["France's capital is Paris. The population is 67 million."]
    answer = adapter.answer(
        query="What is the capital and population of France?",
        documents=docs,
        tenant_id="tenant",
        max_hops=2,
    )
    assert "Paris" in answer and "67 million" in answer


def test_statistical_analysis(adapter):
    docs = ["Values are 10, 20, and 30."]
    result = adapter.analyze(
        query="What is the average and total?", documents=docs, tenant_id="tenant"
    )
    assert result["average"] == 20
    assert result["sum"] == 60
    assert result["count"] == 3
