import os
import sys
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ai"))

spec = importlib.util.spec_from_file_location(
    "filler", os.path.join(ROOT, "ai", "agents", "filler.py")
)
filler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filler)


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
