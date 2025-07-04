import ai.toolset as toolset


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
