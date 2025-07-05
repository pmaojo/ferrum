from ..services import vector_search


class DummyModel:
    def __init__(self, vec):
        self.vec = vec

    def encode(self, question: str):
        class V:
            def __init__(self, v):
                self.v = v

            def tolist(self):
                return self.v

        return V(self.vec)


class DummyClient:
    def __init__(self, hits):
        self.hits = hits
        self.args = None

    def search(self, collection_name: str, query_vector, limit: int):
        self.args = (collection_name, query_vector, limit)
        return self.hits


def test_search_node_returns_id(monkeypatch):
    vec = [1.0, 0.0]
    model = DummyModel(vec)
    hits = [type("Hit", (), {"payload": {"id": "n1"}})()]
    client = DummyClient(hits)

    monkeypatch.setattr(vector_search, "_get_model", lambda: model)
    monkeypatch.setattr(vector_search, "_get_client", lambda: client)

    result = vector_search.search_node("question")

    assert result == "n1"
    assert client.args == ("ferrum-nodes", vec, 1)


def test_search_node_empty(monkeypatch):
    model = DummyModel([0.0])
    client = DummyClient([])

    monkeypatch.setattr(vector_search, "_get_model", lambda: model)
    monkeypatch.setattr(vector_search, "_get_client", lambda: client)

    result = vector_search.search_node("question")

    assert result is None
