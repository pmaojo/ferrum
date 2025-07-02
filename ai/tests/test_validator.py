import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ai"))

import importlib.util
import types

ai_pkg = types.ModuleType("ai")
agents_pkg = types.ModuleType("ai.agents")
agents_pkg.__path__ = [os.path.join(ROOT, "ai", "agents")]
sys.modules["ai"] = ai_pkg
sys.modules["ai.agents"] = agents_pkg

spec = importlib.util.spec_from_file_location(
    "ai.agents.validator",
    os.path.join(ROOT, "ai", "agents", "validator.py"),
)
validator = importlib.util.module_from_spec(spec)
sys.modules["ai.agents.validator"] = validator
spec.loader.exec_module(validator)


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def run(self, *args, **kwargs):
        class R:
            def single(self_inner):
                return {}
        return R()


class FakeDriver:
    def session(self):
        return FakeSession()

    def close(self):
        pass


def test_invalid_structure_returns_false(monkeypatch):
    monkeypatch.setattr(validator, "_get_graph_driver", lambda: FakeDriver())
    result = validator.validate_yaml_with_graph("- just\n- a\n- list")
    assert result is False
