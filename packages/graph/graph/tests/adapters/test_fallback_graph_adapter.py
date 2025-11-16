"""Tests for :mod:`adapters.retrievers.fallback_graph_adapter`."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

# Avoid heavy optional deps during import
sys.modules.setdefault("numpy", ModuleType("numpy"))

MODULE_PATH = Path(__file__).parents[2] / "adapters" / "retrievers" / "fallback_graph_adapter.py"
spec = importlib.util.spec_from_file_location("fallback_graph_adapter", MODULE_PATH)
fallback_graph_adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fallback_graph_adapter
spec.loader.exec_module(fallback_graph_adapter)
FallbackGraphAdapter = fallback_graph_adapter.FallbackGraphAdapter


def test_adapter_initializes():
    adapter = FallbackGraphAdapter()
    assert adapter is not None


def test_index_returns_empty_list():
    adapter = FallbackGraphAdapter()
    result = adapter.index(docs=["doc"], kg_id="kg", tenant_id="t")
    assert result == []


def test_run_returns_empty_string_by_default():
    adapter = FallbackGraphAdapter()
    result = adapter.run(question="q", kg_id="kg", tenant_id="t")
    assert result == ""


def test_run_returns_empty_list_when_requested():
    adapter = FallbackGraphAdapter()
    result = adapter.run(
        question="q", kg_id="kg", tenant_id="t", opts={"return_triples": True}
    )
    assert result == []

