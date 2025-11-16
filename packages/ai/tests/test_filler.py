from ..agents import filler


class FakeResult:
    def __init__(self, record):
        self._record = record

    def single(self):
        return self._record


class FakeSession:
    def __init__(self, record):
        self.record = record

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def run(self, *args, **kwargs):
        return FakeResult(self.record)


class FakeDriver:
    def __init__(self, record):
        self.record = record

    def session(self):
        return FakeSession(self.record)

    def close(self):
        pass


def test_fetch_context_returns_extra_fields(monkeypatch):
    record = {
        "n": "foo",
        "description": "desc",
        "story": "test story",
        "calls": ["bar"],
        "used_by": ["baz"],
    }
    monkeypatch.setattr(filler, "_get_graph_driver", lambda: FakeDriver(record))
    context = filler.fetch_context("foo")
    expected = (
        "- name: foo\n"
        "  description: desc\n"
        "  story: test story\n"
        "  calls: [bar]\n"
        "  used_by: [baz]"
    )
    assert context == expected


def test_fill_code_includes_enriched_context(monkeypatch):
    """Ensure fill_code passes description and story to the LLM."""

    def fake_fetch_context(anchor: str) -> str:
        assert anchor == "foo"
        return "- name: foo\n  description: desc\n  story: test"

    captured = {}

    def fake_call_llm(
        prompt: str, system: str, model: str | None = None, config=None
    ) -> str:
        captured["prompt"] = prompt
        captured["system"] = system
        captured["model"] = model
        captured["config"] = config
        return "code"

    monkeypatch.setattr(filler, "fetch_context", fake_fetch_context)
    monkeypatch.setattr(filler, "call_llm", fake_call_llm)

    result = filler.fill_code("do it", "foo", model="gpt-4")

    assert result == "code"
    assert "description: desc" in captured["prompt"]
    assert "story: test" in captured["prompt"]
    assert captured["model"] == "gpt-4"
    assert captured["config"] is None
