import os
import sys
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ai"))

spec = importlib.util.spec_from_file_location(
    "ai.toolset", os.path.join(ROOT, "ai", "toolset.py")
)
toolset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toolset)


def test_graph_rag_returns_context(monkeypatch):
    t = toolset.Toolset()

    def fake_fetch(anchor):
        assert anchor == "foo"
        return "- name: foo"

    def fake_search(question):
        raise AssertionError("search_node should not be called")

    monkeypatch.setattr(toolset, "fetch_context", fake_fetch)
    monkeypatch.setattr(toolset, "search_node", fake_search)

    result = t.graph_rag("How does `foo` work?")
    assert result == "- name: foo"
